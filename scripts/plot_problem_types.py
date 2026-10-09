"""Render final problem type counts with ReportLab charts and Poppler.

Requires reportlab, a Chinese TTF font, and pdftoppm on PATH.
"""
from collections import Counter
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed_dialogues'


def main():
    rows=[json.loads(x) for x in (DATA/'dialogues.jsonl').open(encoding='utf-8')]
    counts=Counter(t for r in rows for t in set(r['problem_types']))
    stats=json.loads((DATA/'statistics.json').read_text(encoding='utf-8'))
    assert dict(counts)==stats['problem_type_counts']
    font_paths=[Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),
                Path('/usr/share/fonts/truetype/arphic/uming.ttf')]
    font_path=next((p for p in font_paths if p.exists()),None)
    if font_path is None:
        raise RuntimeError('A Chinese TTF font is required; configure font_paths in this script.')
    pdfmetrics.registerFont(TTFont('Chinese',str(font_path)))
    render=shutil.which('pdftoppm')
    if not render:raise RuntimeError('pdftoppm is required to render the chart as PNG.')
    ordered=sorted(counts,key=counts.get,reverse=True)
    classified=sum(bool(r['problem_types']) for r in rows)
    chart=VerticalBarChart()
    chart.x=92;chart.y=88;chart.width=860;chart.height=340
    chart.data=[[counts[k] for k in ordered]]
    chart.categoryAxis.categoryNames=ordered
    chart.categoryAxis.labels.fontName='Chinese';chart.categoryAxis.labels.fontSize=12
    chart.categoryAxis.labels.dy=-12
    chart.categoryAxis.strokeColor=HexColor('#D0D9E3')
    chart.valueAxis.valueMin=0;chart.valueAxis.valueMax=3100;chart.valueAxis.valueStep=500
    chart.valueAxis.labels.fontName='Chinese';chart.valueAxis.labels.fontSize=11
    chart.valueAxis.strokeColor=white
    chart.valueAxis.visibleGrid=True;chart.valueAxis.gridStrokeColor=HexColor('#E6EBF1')
    chart.valueAxis.gridStrokeWidth=.5
    chart.bars[0].fillColor=HexColor('#3977B5');chart.bars[0].strokeColor=None
    chart.barWidth=14;chart.groupSpacing=10
    chart.barLabelFormat=lambda value:f'{value:,.0f}'
    chart.barLabels.fontName='Chinese';chart.barLabels.fontSize=12
    chart.barLabels.fillColor=HexColor('#26364A');chart.barLabels.nudge=10
    drawing=Drawing(1000,550)
    drawing.add(Rect(0,0,1000,550,fillColor=white,strokeColor=None))
    drawing.add(chart)
    drawing.add(String(55,507,'业务类型分布',fontName='Chinese',fontSize=24,fillColor=HexColor('#20334B')))
    drawing.add(String(55,473,f'已采用类型的业务对话：{classified:,} 条',fontName='Chinese',fontSize=13,fillColor=HexColor('#617185')))
    drawing.add(String(92,444,'记录数量',fontName='Chinese',fontSize=11,fillColor=HexColor('#48576A')))
    drawing.add(String(55,29,f'按记录统计；同一记录可计入多个类型。{len(rows)-classified} 条信息不足数据未计入。',fontName='Chinese',fontSize=12,fillColor=HexColor('#617185')))
    with tempfile.TemporaryDirectory(prefix='hmbb-chart-') as tmp:
        pdf=Path(tmp)/'chart.pdf'
        renderPDF.drawToFile(drawing,str(pdf))
        subprocess.run([render,'-png','-singlefile','-r','150',str(pdf),str(DATA/'problem_type_distribution')],check=True)
    print(json.dumps({'counts':dict(counts),'classified_records':classified,'excluded':len(rows)-classified},ensure_ascii=False))


if __name__=='__main__':main()
