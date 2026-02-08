from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QVBoxLayout

try:
    from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPainter

    _HAS_CHARTS = True
except Exception:
    _HAS_CHARTS = False


class BandwidthHistoryDialog(QDialog):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Bandwidth History")
        self.resize(700, 400)

        layout = QVBoxLayout()
        history = self.controller.get_bandwidth_history()
        if _HAS_CHARTS and history:
            chart = _build_chart(history)
            layout.addWidget(chart)
        else:
            table = _build_table(history)
            layout.addWidget(table)
        self.setLayout(layout)


def _build_chart(history: list[tuple[float, float, float | None]]) -> QChartView:
    series = QLineSeries()
    for index, (timestamp, rate, _limit) in enumerate(history):
        series.append(QPointF(index, rate))

    chart = QChart()
    chart.addSeries(series)
    chart.setTitle("Average transfer rate (MB/s)")

    axis_x = QValueAxis()
    axis_x.setLabelFormat("%d")
    axis_x.setTitleText("Samples")
    chart.addAxis(axis_x, chart.AxisOrientation.Bottom)
    series.attachAxis(axis_x)

    axis_y = QValueAxis()
    axis_y.setLabelFormat("%.2f")
    axis_y.setTitleText("MB/s")
    chart.addAxis(axis_y, chart.AxisOrientation.Left)
    series.attachAxis(axis_y)

    view = QChartView(chart)
    view.setRenderHint(QPainter.Antialiasing)
    return view


def _build_table(history: list[tuple[float, float, float | None]]) -> QTableWidget:
    table = QTableWidget(len(history), 3)
    table.setHorizontalHeaderLabels(["Time", "Avg rate (MB/s)", "Limit (MB/s)"])
    for row, (timestamp, rate, limit) in enumerate(history):
        time_text = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        table.setItem(row, 0, QTableWidgetItem(time_text))
        table.setItem(row, 1, QTableWidgetItem(f"{rate:.2f}"))
        table.setItem(row, 2, QTableWidgetItem(f"{limit:.2f}" if limit else "--"))
    return table
