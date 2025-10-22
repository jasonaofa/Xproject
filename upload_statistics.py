#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美术同事上传统计功能
记录和分析美术同事的上传行为
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import socket
import platform

class UploadStatistics:
    """上传统计管理器"""
    
    def __init__(self, stats_file: str = "upload_statistics.json"):
        """
        初始化统计管理器
        
        Args:
            stats_file: 统计数据文件路径
        """
        self.stats_file = stats_file
        self.stats_data = self._load_statistics()
    
    def _load_statistics(self) -> Dict[str, Any]:
        """加载统计数据"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载统计数据失败: {e}")
        
        # 返回默认结构
        return {
            "version": "2.0.0",
            "created_time": datetime.now().isoformat(),
            "total_uploads": 0,
            "total_success": 0,
            "total_failed": 0,
            "total_files": 0,
            "users": {},  # {user_id: user_data}
            "daily_stats": {},  # {date: daily_data}
            "monthly_stats": {},  # {month: monthly_data}
            "upload_history": [],  # 详细上传历史
            "failure_stats": {}  # 失败原因统计
        }
    
    def _save_statistics(self) -> bool:
        """保存统计数据"""
        try:
            # 备份原文件
            if os.path.exists(self.stats_file):
                backup_file = f"{self.stats_file}.backup"
                import shutil
                shutil.copy2(self.stats_file, backup_file)
            
            # 保存新数据
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存统计数据失败: {e}")
            return False
    
    def _get_user_info(self) -> Dict[str, str]:
        """获取用户信息"""
        try:
            user_info = {
                "username": os.getenv('USERNAME', 'Unknown'),
                "computer_name": platform.node(),
                "ip_address": self._get_local_ip(),
                "os": platform.system(),
                "os_version": platform.version()
            }
            return user_info
        except Exception as e:
            print(f"⚠️ 获取用户信息失败: {e}")
            return {"username": "Unknown", "computer_name": "Unknown", "ip_address": "Unknown"}
    
    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def _get_user_id(self, user_info: Dict[str, str]) -> str:
        """生成用户唯一标识"""
        # 使用用户名+计算机名作为唯一标识
        username = user_info.get('username', 'Unknown')
        computer_name = user_info.get('computer_name', 'Unknown')
        return f"{username}@{computer_name}"
    
    def _categorize_error(self, error_message: str) -> str:
        """将错误消息分类为常见错误类型"""
        error_msg_lower = error_message.lower()
        
        # 网络相关错误
        if any(keyword in error_msg_lower for keyword in ['network', '网络', 'connection', 'timeout', '超时', 'unreachable']):
            return "网络连接问题"
        
        # Git相关错误
        if any(keyword in error_msg_lower for keyword in ['git', 'push', 'pull', 'merge', 'conflict', '冲突']):
            return "Git操作失败"
        
        # 权限相关错误
        if any(keyword in error_msg_lower for keyword in ['permission', '权限', 'access', 'denied', 'forbidden']):
            return "权限不足"
        
        # 文件相关错误
        if any(keyword in error_msg_lower for keyword in ['file', '文件', 'path', '路径', 'not found', '找不到']):
            return "文件路径问题"
        
        # GUID相关错误
        if any(keyword in error_msg_lower for keyword in ['guid', 'duplicate', '重复', 'conflict', '冲突']):
            return "GUID冲突"
        
        # 磁盘空间相关错误
        if any(keyword in error_msg_lower for keyword in ['space', '空间', 'disk', '磁盘', 'full']):
            return "磁盘空间不足"
        
        # 其他错误
        return "其他错误"
    
    def record_upload(self, file_count: int, file_paths: List[str], 
                     git_path: str = "", additional_info: Dict[str, Any] = None, 
                     success: bool = True, error_message: str = "") -> bool:
        """
        记录一次上传操作
        
        Args:
            file_count: 上传文件数量
            file_paths: 上传文件路径列表
            git_path: Git仓库路径
            additional_info: 额外信息
            success: 上传是否成功
            error_message: 失败时的错误信息
            
        Returns:
            bool: 是否记录成功
        """
        try:
            user_info = self._get_user_info()
            user_id = self._get_user_id(user_info)
            current_time = datetime.now()
            today = current_time.strftime('%Y-%m-%d')
            this_month = current_time.strftime('%Y-%m')
            
            # 更新总体统计
            self.stats_data["total_uploads"] += 1
            
            # 确保字段存在（兼容旧数据）
            if "total_success" not in self.stats_data:
                self.stats_data["total_success"] = 0
            if "total_failed" not in self.stats_data:
                self.stats_data["total_failed"] = 0
                
            if success:
                self.stats_data["total_success"] += 1
                self.stats_data["total_files"] += file_count
            else:
                self.stats_data["total_failed"] += 1
                # 记录失败原因统计
                if error_message:
                    failure_key = self._categorize_error(error_message)
                    if "failure_stats" not in self.stats_data:
                        self.stats_data["failure_stats"] = {}
                    self.stats_data["failure_stats"][failure_key] = self.stats_data["failure_stats"].get(failure_key, 0) + 1
            
            # 更新用户统计
            if user_id not in self.stats_data["users"]:
                self.stats_data["users"][user_id] = {
                    "user_info": user_info,
                    "first_upload": current_time.isoformat(),
                    "last_upload": current_time.isoformat(),
                    "total_uploads": 0,
                    "success_uploads": 0,
                    "failed_uploads": 0,
                    "total_files": 0,
                    "upload_days": set()
                }
            
            user_data = self.stats_data["users"][user_id]
            user_data["last_upload"] = current_time.isoformat()
            user_data["total_uploads"] += 1
            
            # 确保用户字段存在（兼容旧数据）
            if "success_uploads" not in user_data:
                user_data["success_uploads"] = 0
            if "failed_uploads" not in user_data:
                user_data["failed_uploads"] = 0
            
            if success:
                user_data["success_uploads"] += 1
                user_data["total_files"] += file_count
            else:
                user_data["failed_uploads"] += 1
            user_data["upload_days"] = list(set(user_data.get("upload_days", [])).union({today}))
            
            # 更新每日统计
            if today not in self.stats_data["daily_stats"]:
                self.stats_data["daily_stats"][today] = {
                    "date": today,
                    "uploads": 0,
                    "success": 0,
                    "failed": 0,
                    "files": 0,
                    "users": set()
                }
            
            daily_data = self.stats_data["daily_stats"][today]
            daily_data["uploads"] += 1
            
            # 确保每日统计字段存在（兼容旧数据）
            if "success" not in daily_data:
                daily_data["success"] = 0
            if "failed" not in daily_data:
                daily_data["failed"] = 0
                
            if success:
                daily_data["success"] += 1
                daily_data["files"] += file_count
            else:
                daily_data["failed"] += 1
            daily_data["users"] = list(set(daily_data.get("users", [])).union({user_id}))
            
            # 更新月度统计
            if this_month not in self.stats_data["monthly_stats"]:
                self.stats_data["monthly_stats"][this_month] = {
                    "month": this_month,
                    "uploads": 0,
                    "success": 0,
                    "failed": 0,
                    "files": 0,
                    "users": set()
                }
            
            monthly_data = self.stats_data["monthly_stats"][this_month]
            monthly_data["uploads"] += 1
            
            # 确保月度统计字段存在（兼容旧数据）
            if "success" not in monthly_data:
                monthly_data["success"] = 0
            if "failed" not in monthly_data:
                monthly_data["failed"] = 0
                
            if success:
                monthly_data["success"] += 1
                monthly_data["files"] += file_count
            else:
                monthly_data["failed"] += 1
            monthly_data["users"] = list(set(monthly_data.get("users", [])).union({user_id}))
            
            # 记录详细历史
            upload_record = {
                "timestamp": current_time.isoformat(),
                "user_id": user_id,
                "user_info": user_info,
                "file_count": file_count,
                "file_paths": file_paths[:10],  # 只保存前10个文件路径，避免数据过大
                "git_path": git_path,
                "success": success,
                "error_message": error_message if not success else "",
                "error_category": self._categorize_error(error_message) if not success and error_message else "",
                "additional_info": additional_info or {}
            }
            
            self.stats_data["upload_history"].append(upload_record)
            
            # 保持历史记录数量在合理范围内（最近1000条）
            if len(self.stats_data["upload_history"]) > 1000:
                self.stats_data["upload_history"] = self.stats_data["upload_history"][-1000:]
            
            # 保存数据
            save_success = self._save_statistics()
            
            if save_success:
                status_text = "成功" if success else "失败"
                print(f"📊 统计记录成功: 用户{user_id}上传{status_text} - {file_count}个文件")
            else:
                print(f"⚠️ 统计记录保存失败")
            
            return save_success
            
        except Exception as e:
            print(f"❌ 记录上传统计失败: {e}")
            return False
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """获取统计摘要"""
        try:
            total_users = len(self.stats_data["users"])
            total_uploads = self.stats_data["total_uploads"]
            total_success = self.stats_data.get("total_success", 0)
            total_failed = self.stats_data.get("total_failed", 0)
            total_files = self.stats_data["total_files"]
            
            # 计算成功率
            success_rate = round((total_success / total_uploads * 100), 1) if total_uploads > 0 else 0
            
            # 计算活跃用户（最近7天有上传）
            recent_date = (datetime.now() - timedelta(days=7)).isoformat()
            active_users = 0
            for user_data in self.stats_data["users"].values():
                if user_data.get("last_upload", "") > recent_date:
                    active_users += 1
            
            # 获取最近7天的统计
            recent_stats = self._get_recent_days_stats(7)
            
            # 获取失败原因统计
            failure_stats = self.stats_data.get("failure_stats", {})
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "total_uploads": total_uploads,
                "total_success": total_success,
                "total_failed": total_failed,
                "success_rate": success_rate,
                "total_files": total_files,
                "avg_files_per_upload": round(total_files / total_success, 1) if total_success > 0 else 0,
                "recent_7_days": recent_stats,
                "failure_stats": failure_stats,
                "created_time": self.stats_data.get("created_time"),
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ 获取统计摘要失败: {e}")
            return {}
    
    def _get_recent_days_stats(self, days: int) -> Dict[str, Any]:
        """获取最近N天的统计"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days-1)
            
            recent_uploads = 0
            recent_success = 0
            recent_failed = 0
            recent_files = 0
            recent_users = set()
            daily_breakdown = []
            
            for i in range(days):
                current_date = start_date + timedelta(days=i)
                date_str = current_date.strftime('%Y-%m-%d')
                
                daily_data = self.stats_data["daily_stats"].get(date_str, {})
                day_uploads = daily_data.get("uploads", 0)
                day_success = daily_data.get("success", 0)
                day_failed = daily_data.get("failed", 0)
                day_files = daily_data.get("files", 0)
                day_users = set(daily_data.get("users", []))
                
                recent_uploads += day_uploads
                recent_success += day_success
                recent_failed += day_failed
                recent_files += day_files
                recent_users.update(day_users)
                
                daily_breakdown.append({
                    "date": date_str,
                    "uploads": day_uploads,
                    "success": day_success,
                    "failed": day_failed,
                    "files": day_files,
                    "users": len(day_users)
                })
            
            return {
                "total_uploads": recent_uploads,
                "total_success": recent_success,
                "total_failed": recent_failed,
                "total_files": recent_files,
                "unique_users": len(recent_users),
                "daily_breakdown": daily_breakdown
            }
        except Exception as e:
            print(f"❌ 获取最近天数统计失败: {e}")
            return {}
    
    def get_user_ranking(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户上传排行榜"""
        try:
            user_list = []
            for user_id, user_data in self.stats_data["users"].items():
                success_uploads = user_data.get("success_uploads", user_data["total_uploads"])  # 兼容旧数据
                failed_uploads = user_data.get("failed_uploads", 0)
                success_rate = round((success_uploads / user_data["total_uploads"] * 100), 1) if user_data["total_uploads"] > 0 else 0
                
                user_list.append({
                    "user_id": user_id,
                    "username": user_data["user_info"].get("username", "Unknown"),
                    "computer_name": user_data["user_info"].get("computer_name", "Unknown"),
                    "total_uploads": user_data["total_uploads"],
                    "success_uploads": success_uploads,
                    "failed_uploads": failed_uploads,
                    "success_rate": success_rate,
                    "total_files": user_data["total_files"],
                    "upload_days": len(user_data.get("upload_days", [])),
                    "first_upload": user_data.get("first_upload"),
                    "last_upload": user_data.get("last_upload"),
                    "avg_files_per_upload": round(user_data["total_files"] / success_uploads, 1) if success_uploads > 0 else 0
                })
            
            # 按上传次数排序
            user_list.sort(key=lambda x: x["total_uploads"], reverse=True)
            
            return user_list[:limit]
        except Exception as e:
            print(f"❌ 获取用户排行榜失败: {e}")
            return []
    
    def export_report(self, output_file: str = None) -> str:
        """导出统计报告"""
        try:
            if not output_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"upload_statistics_report_{timestamp}.txt"
            
            summary = self.get_summary_stats()
            ranking = self.get_user_ranking()
            
            report_lines = [
                "=" * 60,
                "美术资源上传统计报告",
                "=" * 60,
                f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"统计开始时间: {summary.get('created_time', 'Unknown')}",
                "",
                "📊 总体统计:",
                f"  总用户数: {summary.get('total_users', 0)}",
                f"  活跃用户数: {summary.get('active_users', 0)} (最近7天)",
                f"  总上传次数: {summary.get('total_uploads', 0)}",
                f"  成功次数: {summary.get('total_success', 0)}",
                f"  失败次数: {summary.get('total_failed', 0)}",
                f"  成功率: {summary.get('success_rate', 0)}%",
                f"  总文件数: {summary.get('total_files', 0)}",
                f"  平均每次成功上传文件数: {summary.get('avg_files_per_upload', 0)}",
                "",
                "📈 最近7天统计:",
                f"  上传次数: {summary.get('recent_7_days', {}).get('total_uploads', 0)}",
                f"  成功次数: {summary.get('recent_7_days', {}).get('total_success', 0)}",
                f"  失败次数: {summary.get('recent_7_days', {}).get('total_failed', 0)}",
                f"  文件数: {summary.get('recent_7_days', {}).get('total_files', 0)}",
                f"  活跃用户: {summary.get('recent_7_days', {}).get('unique_users', 0)}",
                "",
                "🏆 用户排行榜 (按上传次数):",
                "-" * 40
            ]
            
            for i, user in enumerate(ranking, 1):
                report_lines.append(
                    f"  {i:2d}. {user['username']}@{user['computer_name']}\n"
                    f"      上传次数: {user['total_uploads']} (成功: {user.get('success_uploads', user['total_uploads'])}, 失败: {user.get('failed_uploads', 0)}), "
                    f"成功率: {user.get('success_rate', 100)}%\n"
                    f"      文件数: {user['total_files']}, "
                    f"活跃天数: {user['upload_days']}\n"
                    f"      首次上传: {user['first_upload'][:10] if user['first_upload'] else 'Unknown'}, "
                    f"最近上传: {user['last_upload'][:10] if user['last_upload'] else 'Unknown'}"
                )
            
            # 失败原因统计
            failure_stats = summary.get('failure_stats', {})
            if failure_stats:
                report_lines.extend([
                    "",
                    "❌ 失败原因统计:",
                    "-" * 40
                ])
                for reason, count in sorted(failure_stats.items(), key=lambda x: x[1], reverse=True):
                    report_lines.append(f"  {reason}: {count}次")
            
            report_lines.extend([
                "",
                "📅 每日统计明细 (最近7天):",
                "-" * 40
            ])
            
            daily_breakdown = summary.get('recent_7_days', {}).get('daily_breakdown', [])
            for day_data in daily_breakdown[-7:]:  # 最近7天
                report_lines.append(
                    f"  {day_data['date']}: "
                    f"上传{day_data['uploads']}次 (成功{day_data.get('success', day_data['uploads'])}, 失败{day_data.get('failed', 0)}), "
                    f"文件{day_data['files']}个, "
                    f"用户{day_data['users']}人"
                )
            
            report_lines.append("=" * 60)
            
            report_content = "\n".join(report_lines)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"📋 统计报告已导出: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ 导出统计报告失败: {e}")
            return ""


# 全局统计实例
_global_stats = None

def get_statistics_instance() -> UploadStatistics:
    """获取全局统计实例"""
    global _global_stats
    if _global_stats is None:
        _global_stats = UploadStatistics()
    return _global_stats

def record_upload(file_count: int, file_paths: List[str], 
                 git_path: str = "", additional_info: Dict[str, Any] = None,
                 success: bool = True, error_message: str = "") -> bool:
    """便捷函数：记录上传统计"""
    stats = get_statistics_instance()
    return stats.record_upload(file_count, file_paths, git_path, additional_info, success, error_message)

def get_summary_stats() -> Dict[str, Any]:
    """便捷函数：获取统计摘要"""
    stats = get_statistics_instance()
    return stats.get_summary_stats()

def export_report(output_file: str = None) -> str:
    """便捷函数：导出统计报告"""
    stats = get_statistics_instance()
    return stats.export_report(output_file)


if __name__ == "__main__":
    # 测试代码
    stats = UploadStatistics()
    
    # 模拟记录几次上传
    test_files = ["test1.prefab", "test2.mat", "test3.png"]
    stats.record_upload(3, test_files, "G:/test_repo", {"test": True})
    
    # 获取统计摘要
    summary = stats.get_summary_stats()
    print("统计摘要:", json.dumps(summary, ensure_ascii=False, indent=2))
    
    # 获取用户排行榜
    ranking = stats.get_user_ranking()
    print("用户排行榜:", json.dumps(ranking, ensure_ascii=False, indent=2))
    
    # 导出报告
    report_file = stats.export_report()
    print(f"报告文件: {report_file}")
