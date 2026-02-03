"""
Analytics panel for Claude Code Manager.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPainter, QColor, QPen
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis, QPieSeries
from datetime import datetime, timedelta

from core.analytics_manager import AnalyticsManager


class StatCard(QFrame):
    """A card widget for displaying statistics."""

    def __init__(self, title: str, value: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("statCard")
        self.setStyleSheet("""
            #statCard {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 16px;
            }
        """)

        layout = QVBoxLayout(self)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #6495ed;")
        layout.addWidget(self.value_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet("color: #888; font-size: 11px;")
            layout.addWidget(subtitle_label)

    def set_value(self, value: str):
        """Update the value."""
        self.value_label.setText(value)


class AnalyticsPanel(QWidget):
    """Panel for displaying usage analytics."""

    def __init__(self, analytics_manager: AnalyticsManager):
        super().__init__()
        self.analytics_manager = analytics_manager

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Controls
        controls = self.create_controls()
        layout.addWidget(controls)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        # Stats cards
        cards_layout = QHBoxLayout()

        self.sessions_card = StatCard("Total Sessions", "0")
        cards_layout.addWidget(self.sessions_card)

        self.messages_card = StatCard("Total Messages", "0")
        cards_layout.addWidget(self.messages_card)

        self.tokens_card = StatCard("Total Tokens", "0")
        cards_layout.addWidget(self.tokens_card)

        self.cost_card = StatCard("Estimated Cost", "$0.00")
        cards_layout.addWidget(self.cost_card)

        content_layout.addLayout(cards_layout)

        # Charts row 1
        charts_row1 = QHBoxLayout()

        # Activity chart
        activity_group = QGroupBox("Daily Activity")
        activity_layout = QVBoxLayout(activity_group)
        self.activity_chart = QChartView()
        self.activity_chart.setMinimumHeight(300)
        self.activity_chart.setRenderHint(QPainter.Antialiasing)
        activity_layout.addWidget(self.activity_chart)
        charts_row1.addWidget(activity_group)

        # Token usage chart
        tokens_group = QGroupBox("Token Usage by Day")
        tokens_layout = QVBoxLayout(tokens_group)
        self.tokens_chart = QChartView()
        self.tokens_chart.setMinimumHeight(300)
        self.tokens_chart.setRenderHint(QPainter.Antialiasing)
        tokens_layout.addWidget(self.tokens_chart)
        charts_row1.addWidget(tokens_group)

        content_layout.addLayout(charts_row1)

        # Charts row 2
        charts_row2 = QHBoxLayout()

        # Model usage pie chart
        model_group = QGroupBox("Usage by Model")
        model_layout = QVBoxLayout(model_group)
        self.model_chart = QChartView()
        self.model_chart.setMinimumHeight(300)
        self.model_chart.setRenderHint(QPainter.Antialiasing)
        model_layout.addWidget(self.model_chart)
        charts_row2.addWidget(model_group)

        # Hour distribution
        hour_group = QGroupBox("Activity by Hour")
        hour_layout = QVBoxLayout(hour_group)
        self.hour_chart = QChartView()
        self.hour_chart.setMinimumHeight(300)
        self.hour_chart.setRenderHint(QPainter.Antialiasing)
        hour_layout.addWidget(self.hour_chart)
        charts_row2.addWidget(hour_group)

        content_layout.addLayout(charts_row2)

        # Details table
        details_group = QGroupBox("Model Usage Details")
        details_layout = QVBoxLayout(details_group)

        self.details_table = QTableWidget()
        self.details_table.setColumnCount(6)
        self.details_table.setHorizontalHeaderLabels([
            "Model", "Input Tokens", "Output Tokens", "Cache Read", "Cache Create", "Est. Cost"
        ])
        self.details_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        details_layout.addWidget(self.details_table)

        content_layout.addWidget(details_group)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def create_controls(self) -> QWidget:
        """Create the controls bar."""
        controls = QFrame()
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 8)

        # Time range selector
        layout.addWidget(QLabel("Time Range:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"])
        self.time_range_combo.currentIndexChanged.connect(self.refresh)
        layout.addWidget(self.time_range_combo)

        layout.addStretch()

        # Export button
        export_btn = QPushButton("Export Data")
        export_btn.clicked.connect(self.export_data)
        layout.addWidget(export_btn)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        return controls

    def refresh(self):
        """Refresh analytics data."""
        # Get time range
        range_map = {0: 7, 1: 30, 2: 90, 3: 365}
        days = range_map.get(self.time_range_combo.currentIndex(), 30)

        # Update stats cards
        summary = self.analytics_manager.get_summary_stats()
        self.sessions_card.set_value(str(summary['total_sessions']))
        self.messages_card.set_value(str(summary['total_messages']))

        total_tokens = (
            summary['total_input_tokens'] +
            summary['total_output_tokens'] +
            summary['total_cache_read_tokens'] +
            summary['total_cache_create_tokens']
        )
        self.tokens_card.set_value(self.format_number(total_tokens))
        self.cost_card.set_value(f"${summary['total_cost']:.2f}")

        # Update charts
        self.update_activity_chart(days)
        self.update_tokens_chart(days)
        self.update_model_chart()
        self.update_hour_chart(summary.get('hour_distribution', {}))

        # Update details table
        self.update_details_table()

    def update_activity_chart(self, days: int):
        """Update the activity chart."""
        activity = self.analytics_manager.get_daily_activity(days)

        chart = QChart()
        chart.setBackgroundBrush(QColor("#252526"))
        chart.setTitleBrush(QColor("#dcdcdc"))
        chart.legend().setLabelColor(QColor("#dcdcdc"))

        # Messages series
        messages_series = QLineSeries()
        messages_series.setName("Messages")
        messages_series.setColor(QColor("#6495ed"))

        # Sessions series
        sessions_series = QLineSeries()
        sessions_series.setName("Sessions")
        sessions_series.setColor(QColor("#50c878"))

        for i, day in enumerate(activity):
            messages_series.append(i, day.message_count)
            sessions_series.append(i, day.session_count * 10)  # Scale for visibility

        chart.addSeries(messages_series)
        chart.addSeries(sessions_series)

        chart.createDefaultAxes()

        # Style axes
        for axis in chart.axes():
            axis.setLabelsColor(QColor("#dcdcdc"))
            axis.setGridLineColor(QColor("#3d3d3d"))

        self.activity_chart.setChart(chart)

    def update_tokens_chart(self, days: int):
        """Update the tokens chart."""
        tokens_data = self.analytics_manager.get_tokens_by_day(days)

        chart = QChart()
        chart.setBackgroundBrush(QColor("#252526"))
        chart.legend().setLabelColor(QColor("#dcdcdc"))

        bar_set = QBarSet("Tokens")
        bar_set.setColor(QColor("#6495ed"))

        categories = []
        for data in tokens_data[-14:]:  # Last 14 days
            bar_set.append(data['total_tokens'] / 1000)  # In thousands
            categories.append(data['date'][-5:])  # MM-DD

        series = QBarSeries()
        series.append(bar_set)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor("#dcdcdc"))
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("Tokens (K)")
        axis_y.setLabelsColor(QColor("#dcdcdc"))
        axis_y.setGridLineColor(QColor("#3d3d3d"))
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        self.tokens_chart.setChart(chart)

    def update_model_chart(self):
        """Update the model usage pie chart."""
        usage = self.analytics_manager.get_model_usage()

        chart = QChart()
        chart.setBackgroundBrush(QColor("#252526"))
        chart.legend().setLabelColor(QColor("#dcdcdc"))

        series = QPieSeries()

        colors = [QColor("#6495ed"), QColor("#50c878"), QColor("#ffa500"), QColor("#ff6b6b")]

        for i, (model, data) in enumerate(usage.items()):
            total = data.input_tokens + data.output_tokens
            if total > 0:
                slice = series.append(model.split('-')[1][:6], total)
                slice.setColor(colors[i % len(colors)])
                slice.setLabelColor(QColor("#dcdcdc"))

        chart.addSeries(series)
        self.model_chart.setChart(chart)

    def update_hour_chart(self, hour_distribution: dict):
        """Update the hour distribution chart."""
        chart = QChart()
        chart.setBackgroundBrush(QColor("#252526"))
        chart.legend().hide()

        bar_set = QBarSet("Sessions")
        bar_set.setColor(QColor("#6495ed"))

        categories = []
        for hour in range(24):
            count = hour_distribution.get(str(hour), 0)
            bar_set.append(count)
            categories.append(f"{hour:02d}")

        series = QBarSeries()
        series.append(bar_set)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsColor(QColor("#dcdcdc"))
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#dcdcdc"))
        axis_y.setGridLineColor(QColor("#3d3d3d"))
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        self.hour_chart.setChart(chart)

    def update_details_table(self):
        """Update the model details table."""
        usage = self.analytics_manager.get_model_usage()

        self.details_table.setRowCount(len(usage))

        for i, (model, data) in enumerate(usage.items()):
            cost = self.analytics_manager.calculate_cost(
                model, data.input_tokens, data.output_tokens,
                data.cache_read_tokens, data.cache_creation_tokens
            )

            self.details_table.setItem(i, 0, QTableWidgetItem(model))
            self.details_table.setItem(i, 1, QTableWidgetItem(self.format_number(data.input_tokens)))
            self.details_table.setItem(i, 2, QTableWidgetItem(self.format_number(data.output_tokens)))
            self.details_table.setItem(i, 3, QTableWidgetItem(self.format_number(data.cache_read_tokens)))
            self.details_table.setItem(i, 4, QTableWidgetItem(self.format_number(data.cache_creation_tokens)))
            self.details_table.setItem(i, 5, QTableWidgetItem(f"${cost:.4f}"))

    def format_number(self, num: int) -> str:
        """Format large numbers for display."""
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)

    def export_data(self):
        """Export analytics data."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Analytics",
            f"claude_analytics_{datetime.now().strftime('%Y%m%d')}.json",
            "JSON Files (*.json);;CSV Files (*.csv)"
        )

        if filepath:
            format_type = 'csv' if filepath.endswith('.csv') else 'json'
            if self.analytics_manager.export_analytics(filepath, format_type):
                QMessageBox.information(self, "Success", f"Analytics exported to {filepath}")
            else:
                QMessageBox.warning(self, "Error", "Failed to export analytics")
