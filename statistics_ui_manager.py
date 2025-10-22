#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计功能UI管理器
负责处理主程序中的统计相关界面操作
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from upload_statistics import get_summary_stats, get_statistics_instance, export_report

class StatisticsUIManager:
    """统计功能UI管理器"""
    
    def __init__(self, parent_window):
        """
        初始化统计UI管理器
        
        Args:
            parent_window: 父窗口对象（主程序窗口）
        """
        self.parent = parent_window
    
    def show_statistics_dialog(self):
        """显示统计信息对话框"""
        try:
            # 获取统计数据
            summary = get_summary_stats()
            stats_instance = get_statistics_instance()
            ranking = stats_instance.get_user_ranking(10)
            
            if not summary:
                QMessageBox.information(self.parent, "统计信息", "暂无上传统计数据")
                return
            
            # 构建统计信息文本
            stats_text = self._build_statistics_text(summary, ranking)
            
            # 显示统计信息对话框
            msg_box = QMessageBox(self.parent)
            msg_box.setWindowTitle("上传统计信息")
            msg_box.setText(stats_text)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
            
        except Exception as e:
            QMessageBox.critical(self.parent, "错误", f"查看统计信息失败:\n{str(e)}")
            print(f"❌ 查看统计信息失败: {e}")
    
    def export_statistics_report(self):
        """导出统计报告"""
        try:
            # 选择导出文件路径
            file_path, _ = QFileDialog.getSaveFileName(
                self.parent, 
                "导出统计报告", 
                f"upload_statistics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "文本文件 (*.txt);;所有文件 (*.*)"
            )
            
            if file_path:
                # 导出报告
                result_file = export_report(file_path)
                if result_file:
                    reply = QMessageBox.question(
                        self.parent, 
                        "导出成功", 
                        f"统计报告已成功导出到:\n{result_file}\n\n是否要打开文件？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        self._open_file(result_file)
                else:
                    QMessageBox.critical(self.parent, "导出失败", "统计报告导出失败，请检查文件权限")
            
        except Exception as e:
            QMessageBox.critical(self.parent, "错误", f"导出统计报告失败:\n{str(e)}")
            print(f"❌ 导出统计报告失败: {e}")
    
    def _build_statistics_text(self, summary: dict, ranking: list) -> str:
        """构建统计信息文本"""
        stats_text = f"""📊 美术同事上传统计

🔢 总体统计:
• 总用户数: {summary.get('total_users', 0)} 人
• 活跃用户数: {summary.get('active_users', 0)} 人 (最近7天)
• 总上传次数: {summary.get('total_uploads', 0)} 次
• 成功次数: {summary.get('total_success', 0)} 次
• 失败次数: {summary.get('total_failed', 0)} 次
• 成功率: {summary.get('success_rate', 0)}%
• 总文件数: {summary.get('total_files', 0)} 个
• 平均每次成功上传: {summary.get('avg_files_per_upload', 0)} 个文件

📈 最近7天统计:
• 上传次数: {summary.get('recent_7_days', {}).get('total_uploads', 0)} 次
• 成功次数: {summary.get('recent_7_days', {}).get('total_success', 0)} 次
• 失败次数: {summary.get('recent_7_days', {}).get('total_failed', 0)} 次
• 文件数: {summary.get('recent_7_days', {}).get('total_files', 0)} 个
• 活跃用户: {summary.get('recent_7_days', {}).get('unique_users', 0)} 人

🏆 用户排行榜 (前5名):"""
        
        for i, user in enumerate(ranking[:5], 1):
            stats_text += f"""
{i}. {user['username']}@{user['computer_name']}
   上传次数: {user['total_uploads']} (成功: {user.get('success_uploads', user['total_uploads'])}, 失败: {user.get('failed_uploads', 0)})
   成功率: {user.get('success_rate', 100)}%, 文件数: {user['total_files']}, 活跃天数: {user['upload_days']}"""
        
        # 添加失败原因统计
        failure_stats = summary.get('failure_stats', {})
        if failure_stats:
            stats_text += "\n\n❌ 主要失败原因:"
            for reason, count in sorted(failure_stats.items(), key=lambda x: x[1], reverse=True)[:3]:
                stats_text += f"\n• {reason}: {count}次"
        
        return stats_text
    
    def _open_file(self, file_path: str):
        """打开文件"""
        try:
            import subprocess
            import platform
            if platform.system() == 'Windows':
                os.startfile(file_path)
            else:
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            print(f"⚠️ 打开文件失败: {e}")


class StatisticsRecorder:
    """统计记录器 - 负责记录上传统计"""
    
    @staticmethod
    def record_upload_success(file_count: int, file_paths: list, git_path: str = "", additional_info: dict = None):
        """记录成功上传"""
        try:
            from upload_statistics import record_upload
            file_names = [os.path.basename(f) for f in file_paths]  # 只记录文件名，保护隐私
            record_upload(
                file_count=file_count,
                file_paths=file_names,
                git_path=os.path.basename(git_path) if git_path else "",  # 只记录仓库名
                additional_info=additional_info or {},
                success=True
            )
            print(f"📊 已记录上传统计: 成功上传{file_count}个文件")
            return True
        except Exception as e:
            print(f"⚠️ 记录成功上传统计失败: {e}")
            return False
    
    @staticmethod
    def record_upload_failure(file_count: int, file_paths: list, error_message: str, git_path: str = "", additional_info: dict = None):
        """记录失败上传"""
        try:
            from upload_statistics import record_upload
            file_names = [os.path.basename(f) for f in file_paths]  # 只记录文件名，保护隐私
            record_upload(
                file_count=file_count,
                file_paths=file_names,
                git_path=os.path.basename(git_path) if git_path else "",  # 只记录仓库名
                additional_info=additional_info or {},
                success=False,
                error_message=error_message
            )
            print(f"📊 已记录上传统计: 失败上传{file_count}个文件")
            return True
        except Exception as e:
            print(f"⚠️ 记录失败上传统计失败: {e}")
            return False


# 便捷函数，供主程序调用
def create_statistics_ui_manager(parent_window):
    """创建统计UI管理器实例"""
    return StatisticsUIManager(parent_window)

def record_successful_upload(file_count: int, file_paths: list, git_path: str = "", additional_info: dict = None):
    """记录成功上传（便捷函数）"""
    return StatisticsRecorder.record_upload_success(file_count, file_paths, git_path, additional_info)

def record_failed_upload(file_count: int, file_paths: list, error_message: str, git_path: str = "", additional_info: dict = None):
    """记录失败上传（便捷函数）"""
    return StatisticsRecorder.record_upload_failure(file_count, file_paths, error_message, git_path, additional_info)


if __name__ == "__main__":
    # 测试代码
    print("统计UI管理器模块测试")
    
    # 测试记录功能
    test_files = ["test1.prefab", "test2.mat"]
    record_successful_upload(2, test_files, "TestRepo", {"test": True})
    record_failed_upload(1, ["fail.png"], "Network timeout", "TestRepo", {"test": True})
    
    print("测试完成")

