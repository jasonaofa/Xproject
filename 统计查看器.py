#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美术同事上传统计查看器
独立的统计查看工具，方便管理员查看上传统计
"""

import sys
import os
import json
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QWidget, QPushButton, QTextEdit, QLabel, QTabWidget,
                           QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog,
                           QSplitter, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from upload_statistics import UploadStatistics, get_summary_stats, export_report

class StatisticsViewer(QMainWindow):
    """统计查看器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.stats = UploadStatistics()
        self.init_ui()
        self.load_statistics()
        
        # 设置定时器自动刷新数据
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_statistics)
        self.refresh_timer.start(30000)  # 30秒刷新一次
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("美术资源上传统计查看器 v1.0.7")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部按钮栏
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.load_statistics)
        button_layout.addWidget(self.refresh_btn)
        
        self.export_btn = QPushButton("导出报告")
        self.export_btn.clicked.connect(self.export_report)
        button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        
        self.status_label = QLabel("准备就绪")
        button_layout.addWidget(self.status_label)
        
        main_layout.addLayout(button_layout)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 概览标签页
        self.create_overview_tab()
        
        # 用户排行榜标签页
        self.create_ranking_tab()
        
        # 详细统计标签页
        self.create_details_tab()
    
    def create_overview_tab(self):
        """创建概览标签页"""
        overview_widget = QWidget()
        layout = QVBoxLayout(overview_widget)
        
        # 创建统计卡片
        cards_layout = QGridLayout()
        
        # 总体统计卡片
        self.total_stats_group = QGroupBox("📊 总体统计")
        self.total_stats_layout = QVBoxLayout(self.total_stats_group)
        self.total_stats_text = QLabel("加载中...")
        self.total_stats_text.setFont(QFont("Consolas", 10))
        self.total_stats_layout.addWidget(self.total_stats_text)
        cards_layout.addWidget(self.total_stats_group, 0, 0)
        
        # 最近7天统计卡片
        self.recent_stats_group = QGroupBox("📈 最近7天")
        self.recent_stats_layout = QVBoxLayout(self.recent_stats_group)
        self.recent_stats_text = QLabel("加载中...")
        self.recent_stats_text.setFont(QFont("Consolas", 10))
        self.recent_stats_layout.addWidget(self.recent_stats_text)
        cards_layout.addWidget(self.recent_stats_group, 0, 1)
        
        layout.addLayout(cards_layout)
        
        # 每日统计图表（简单文本显示）
        self.daily_chart_group = QGroupBox("📅 每日统计趋势")
        self.daily_chart_layout = QVBoxLayout(self.daily_chart_group)
        self.daily_chart_text = QTextEdit()
        self.daily_chart_text.setFont(QFont("Consolas", 9))
        self.daily_chart_text.setMaximumHeight(200)
        self.daily_chart_layout.addWidget(self.daily_chart_text)
        layout.addWidget(self.daily_chart_group)
        
        self.tab_widget.addTab(overview_widget, "概览")
    
    def create_ranking_tab(self):
        """创建用户排行榜标签页"""
        ranking_widget = QWidget()
        layout = QVBoxLayout(ranking_widget)
        
        # 排行榜表格
        self.ranking_table = QTableWidget()
        self.ranking_table.setColumnCount(10)
        self.ranking_table.setHorizontalHeaderLabels([
            "排名", "用户名", "计算机", "上传次数", "成功次数", "失败次数", "成功率", "文件总数", "活跃天数", "最近上传"
        ])
        
        # 设置表格属性
        self.ranking_table.setAlternatingRowColors(True)
        self.ranking_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ranking_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.ranking_table)
        
        self.tab_widget.addTab(ranking_widget, "用户排行榜")
    
    def create_details_tab(self):
        """创建详细统计标签页"""
        details_widget = QWidget()
        layout = QVBoxLayout(details_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：统计详情
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 统计详情文本
        details_group = QGroupBox("📋 详细统计信息")
        details_layout = QVBoxLayout(details_group)
        self.details_text = QTextEdit()
        self.details_text.setFont(QFont("Consolas", 9))
        details_layout.addWidget(self.details_text)
        left_layout.addWidget(details_group)
        
        splitter.addWidget(left_widget)
        
        # 右侧：最近上传历史
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        history_group = QGroupBox("🕐 最近上传历史")
        history_layout = QVBoxLayout(history_group)
        self.history_text = QTextEdit()
        self.history_text.setFont(QFont("Consolas", 8))
        history_layout.addWidget(self.history_text)
        right_layout.addWidget(history_group)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter)
        
        self.tab_widget.addTab(details_widget, "详细信息")
    
    def load_statistics(self):
        """加载统计数据"""
        try:
            self.status_label.setText("正在加载...")
            QApplication.processEvents()
            
            # 重新加载统计数据
            self.stats = UploadStatistics()
            summary = self.stats.get_summary_stats()
            ranking = self.stats.get_user_ranking(20)
            
            if not summary:
                self.status_label.setText("暂无数据")
                return
            
            # 更新概览页面
            self.update_overview(summary)
            
            # 更新排行榜
            self.update_ranking_table(ranking)
            
            # 更新详细信息
            self.update_details(summary)
            
            self.status_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.status_label.setText(f"加载失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载统计数据失败:\n{str(e)}")
    
    def update_overview(self, summary: dict):
        """更新概览页面"""
        try:
            # 更新总体统计
            total_text = f"""用户总数: {summary.get('total_users', 0)} 人
活跃用户: {summary.get('active_users', 0)} 人
上传总次数: {summary.get('total_uploads', 0)} 次
成功次数: {summary.get('total_success', 0)} 次
失败次数: {summary.get('total_failed', 0)} 次
成功率: {summary.get('success_rate', 0)}%
文件总数: {summary.get('total_files', 0)} 个
平均文件数: {summary.get('avg_files_per_upload', 0)} 个/次"""
            self.total_stats_text.setText(total_text)
            
            # 更新最近7天统计
            recent_data = summary.get('recent_7_days', {})
            recent_text = f"""上传次数: {recent_data.get('total_uploads', 0)} 次
成功次数: {recent_data.get('total_success', 0)} 次
失败次数: {recent_data.get('total_failed', 0)} 次
文件数量: {recent_data.get('total_files', 0)} 个
活跃用户: {recent_data.get('unique_users', 0)} 人"""
            self.recent_stats_text.setText(recent_text)
            
            # 更新每日趋势
            daily_breakdown = recent_data.get('daily_breakdown', [])
            chart_text = "日期       上传次数  成功  失败  文件数  用户数\n"
            chart_text += "-" * 45 + "\n"
            
            for day_data in daily_breakdown[-7:]:
                chart_text += f"{day_data['date']}  {day_data['uploads']:4d}     {day_data.get('success', day_data['uploads']):3d}  {day_data.get('failed', 0):3d}  {day_data['files']:4d}   {day_data['users']:3d}\n"
            
            self.daily_chart_text.setText(chart_text)
            
        except Exception as e:
            print(f"更新概览失败: {e}")
    
    def update_ranking_table(self, ranking: list):
        """更新排行榜表格"""
        try:
            self.ranking_table.setRowCount(len(ranking))
            
            for row, user in enumerate(ranking):
                self.ranking_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                self.ranking_table.setItem(row, 1, QTableWidgetItem(user.get('username', 'Unknown')))
                self.ranking_table.setItem(row, 2, QTableWidgetItem(user.get('computer_name', 'Unknown')))
                self.ranking_table.setItem(row, 3, QTableWidgetItem(str(user.get('total_uploads', 0))))
                self.ranking_table.setItem(row, 4, QTableWidgetItem(str(user.get('success_uploads', user.get('total_uploads', 0)))))
                self.ranking_table.setItem(row, 5, QTableWidgetItem(str(user.get('failed_uploads', 0))))
                self.ranking_table.setItem(row, 6, QTableWidgetItem(f"{user.get('success_rate', 100)}%"))
                self.ranking_table.setItem(row, 7, QTableWidgetItem(str(user.get('total_files', 0))))
                self.ranking_table.setItem(row, 8, QTableWidgetItem(str(user.get('upload_days', 0))))
                
                last_upload = user.get('last_upload', '')
                if last_upload:
                    last_upload_date = last_upload[:10]  # 只显示日期部分
                else:
                    last_upload_date = 'Unknown'
                self.ranking_table.setItem(row, 9, QTableWidgetItem(last_upload_date))
            
            # 调整列宽
            self.ranking_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"更新排行榜失败: {e}")
    
    def update_details(self, summary: dict):
        """更新详细信息"""
        try:
            # 详细统计信息
            details_text = f"""📊 详细统计报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== 总体统计 ===
统计开始时间: {summary.get('created_time', 'Unknown')[:19]}
总用户数: {summary.get('total_users', 0)} 人
活跃用户数: {summary.get('active_users', 0)} 人 (最近7天)
总上传次数: {summary.get('total_uploads', 0)} 次
成功次数: {summary.get('total_success', 0)} 次
失败次数: {summary.get('total_failed', 0)} 次
成功率: {summary.get('success_rate', 0)}%
总文件数: {summary.get('total_files', 0)} 个
平均每次成功上传文件数: {summary.get('avg_files_per_upload', 0)} 个

=== 最近7天统计 ===
上传次数: {summary.get('recent_7_days', {}).get('total_uploads', 0)} 次
成功次数: {summary.get('recent_7_days', {}).get('total_success', 0)} 次
失败次数: {summary.get('recent_7_days', {}).get('total_failed', 0)} 次
文件数: {summary.get('recent_7_days', {}).get('total_files', 0)} 个
活跃用户: {summary.get('recent_7_days', {}).get('unique_users', 0)} 人

=== 失败原因统计 ==="""
            
            failure_stats = summary.get('failure_stats', {})
            if failure_stats:
                for reason, count in sorted(failure_stats.items(), key=lambda x: x[1], reverse=True):
                    details_text += f"\n{reason}: {count}次"
            else:
                details_text += "\n暂无失败记录"
            
            details_text += "\n\n=== 每日明细 ==="
            
            daily_breakdown = summary.get('recent_7_days', {}).get('daily_breakdown', [])
            for day_data in daily_breakdown[-7:]:
                details_text += f"""
{day_data['date']}: 上传{day_data['uploads']}次 (成功{day_data.get('success', day_data['uploads'])}, 失败{day_data.get('failed', 0)}), 文件{day_data['files']}个, 用户{day_data['users']}人"""
            
            self.details_text.setText(details_text)
            
            # 最近上传历史
            history_text = "📋 最近上传历史 (最新10条):\n\n"
            upload_history = self.stats.stats_data.get('upload_history', [])
            
            for record in upload_history[-10:]:
                timestamp = record.get('timestamp', '')[:19]  # 去掉毫秒
                user_info = record.get('user_info', {})
                username = user_info.get('username', 'Unknown')
                computer_name = user_info.get('computer_name', 'Unknown')
                file_count = record.get('file_count', 0)
                success = record.get('success', True)
                error_message = record.get('error_message', '')
                error_category = record.get('error_category', '')
                
                status_icon = "✅" if success else "❌"
                history_text += f"{timestamp} - {username}@{computer_name} {status_icon}\n"
                history_text += f"  上传文件: {file_count}个 ({'成功' if success else '失败'})\n"
                
                if not success and error_category:
                    history_text += f"  失败原因: {error_category}\n"
                
                file_paths = record.get('file_paths', [])
                if file_paths:
                    history_text += f"  文件示例: {', '.join(file_paths[:3])}"
                    if len(file_paths) > 3:
                        history_text += f" 等{len(file_paths)}个文件"
                history_text += "\n\n"
            
            self.history_text.setText(history_text)
            
        except Exception as e:
            print(f"更新详细信息失败: {e}")
    
    def export_report(self):
        """导出统计报告"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "导出统计报告", 
                f"upload_statistics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "文本文件 (*.txt);;所有文件 (*.*)"
            )
            
            if file_path:
                result_file = export_report(file_path)
                if result_file:
                    reply = QMessageBox.question(
                        self, 
                        "导出成功", 
                        f"统计报告已成功导出到:\n{result_file}\n\n是否要打开文件？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        os.startfile(result_file)
                else:
                    QMessageBox.critical(self, "导出失败", "统计报告导出失败，请检查文件权限")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出统计报告失败:\n{str(e)}")

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("美术资源上传统计查看器")
    
    # 设置应用图标（如果有的话）
    try:
        if os.path.exists("app_icon_bai.ico"):
            from PyQt5.QtGui import QIcon
            app.setWindowIcon(QIcon("app_icon_bai.ico"))
    except:
        pass
    
    viewer = StatisticsViewer()
    viewer.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
