#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI集成示例：展示如何在美术资源管理器界面中集成CRLF处理功能
"""

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QTextEdit, QMessageBox, 
                            QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import sys
import os


class CRLFFixThread(QThread):
    """CRLF修复线程"""
    
    progress_updated = pyqtSignal(str)  # 进度更新信号
    fix_completed = pyqtSignal(bool, str)  # 修复完成信号
    
    def __init__(self, git_path, fix_mode="quick"):
        super().__init__()
        self.git_path = git_path
        self.fix_mode = fix_mode
    
    def run(self):
        """执行CRLF修复"""
        try:
            self.progress_updated.emit("🔧 正在初始化CRLF修复器...")
            
            # 这里会导入并使用我们的CRLF修复模块
            from crlf_auto_fix import CRLFAutoFixer
            
            fixer = CRLFAutoFixer(self.git_path)
            
            if self.fix_mode == "quick":
                self.progress_updated.emit("⚡ 执行快速CRLF修复...")
                success, message = fixer.quick_fix_common_issues()
            else:
                # 这里可以添加其他修复模式
                success, message = fixer.quick_fix_common_issues()
            
            self.progress_updated.emit("✅ CRLF修复完成")
            self.fix_completed.emit(success, message)
            
        except Exception as e:
            self.progress_updated.emit(f"❌ 修复过程中出现错误")
            self.fix_completed.emit(False, f"修复失败: {str(e)}")


class ArtResourceManagerWithCRLF(QMainWindow):
    """集成CRLF功能的美术资源管理器界面示例"""
    
    def __init__(self):
        super().__init__()
        self.git_path = ""
        self.crlf_fix_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("美术资源管理器 - 集成CRLF自动修复")
        self.setGeometry(100, 100, 800, 600)
        
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局
        main_layout = QVBoxLayout(main_widget)
        
        # 添加原有的功能区域
        self.create_original_features(main_layout)
        
        # 添加新的CRLF功能区域
        self.create_crlf_features(main_layout)
        
        # 日志显示区域
        self.create_log_area(main_layout)
    
    def create_original_features(self, layout):
        """创建原有功能区域（模拟）"""
        original_group = QGroupBox("📁 原有功能")
        original_layout = QVBoxLayout(original_group)
        
        # 模拟原有按钮
        btn_layout = QHBoxLayout()
        
        self.btn_select_files = QPushButton("选择文件")
        self.btn_check_push = QPushButton("检查并推送")
        self.btn_pull = QPushButton("拉取更新")
        
        btn_layout.addWidget(self.btn_select_files)
        btn_layout.addWidget(self.btn_check_push)
        btn_layout.addWidget(self.btn_pull)
        btn_layout.addStretch()
        
        original_layout.addLayout(btn_layout)
        
        # 连接原有按钮的信号（在这里集成CRLF处理）
        self.btn_check_push.clicked.connect(self.enhanced_check_and_push)
        
        layout.addWidget(original_group)
    
    def create_crlf_features(self, layout):
        """创建CRLF功能区域"""
        crlf_group = QGroupBox("🔧 CRLF问题处理")
        crlf_layout = QVBoxLayout(crlf_group)
        
        # 选项
        options_layout = QHBoxLayout()
        self.cb_auto_fix = QCheckBox("自动修复CRLF问题")
        self.cb_auto_fix.setChecked(True)
        self.cb_preventive = QCheckBox("推送前预防性修复")
        self.cb_preventive.setChecked(True)
        
        options_layout.addWidget(self.cb_auto_fix)
        options_layout.addWidget(self.cb_preventive)
        options_layout.addStretch()
        
        crlf_layout.addLayout(options_layout)
        
        # 手动修复按钮
        manual_layout = QHBoxLayout()
        
        self.btn_quick_fix = QPushButton("⚡ 快速修复")
        self.btn_quick_fix.setToolTip("预防性修复常见的CRLF问题")
        self.btn_quick_fix.clicked.connect(self.manual_quick_fix)
        
        self.btn_smart_fix = QPushButton("🧠 智能修复")
        self.btn_smart_fix.setToolTip("基于错误信息的智能修复")
        self.btn_smart_fix.setEnabled(False)  # 需要错误信息时才启用
        
        self.btn_reset_config = QPushButton("🔄 重置配置")
        self.btn_reset_config.setToolTip("重置Git换行符配置")
        
        manual_layout.addWidget(self.btn_quick_fix)
        manual_layout.addWidget(self.btn_smart_fix)
        manual_layout.addWidget(self.btn_reset_config)
        manual_layout.addStretch()
        
        crlf_layout.addLayout(manual_layout)
        
        layout.addWidget(crlf_group)
    
    def create_log_area(self, layout):
        """创建日志显示区域"""
        log_group = QGroupBox("📋 操作日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
    
    def enhanced_check_and_push(self):
        """增强版检查并推送（集成CRLF处理）"""
        self.log("🚀 开始检查并推送...")
        
        # 如果启用了预防性修复
        if self.cb_preventive.isChecked():
            self.log("🔧 执行预防性CRLF修复...")
            self.manual_quick_fix(silent=True)
        
        # 这里模拟原有的推送逻辑
        self.log("📝 执行文件检查...")
        self.log("📤 开始推送文件...")
        
        # 模拟可能遇到CRLF错误
        import random
        if random.choice([True, False]) and self.cb_auto_fix.isChecked():
            self.log("⚠️ 检测到CRLF问题...")
            self.handle_crlf_error_during_push()
        else:
            self.log("✅ 推送完成")
    
    def handle_crlf_error_during_push(self):
        """处理推送过程中遇到的CRLF错误"""
        self.log("🔧 启动自动CRLF修复...")
        
        # 这里会调用CRLF修复逻辑
        if self.cb_auto_fix.isChecked():
            self.log("✅ CRLF问题已自动修复")
            self.log("🔄 重新尝试推送...")
            self.log("✅ 推送成功")
        else:
            self.log("❌ 未启用自动修复，需要手动处理")
            self.show_crlf_error_dialog()
    
    def manual_quick_fix(self, silent=False):
        """手动快速修复"""
        if not silent:
            self.log("⚡ 开始快速CRLF修复...")
        
        # 设置Git路径（实际应用中从配置获取）
        self.git_path = r"G:\minirepo\AssetRuntime_Branch08\assetruntime\CommonResource"
        
        if not os.path.exists(self.git_path):
            if not silent:
                self.log("❌ Git仓库路径不存在")
                QMessageBox.warning(self, "错误", "Git仓库路径不存在，请先配置正确的路径")
            return
        
        # 启动修复线程
        self.crlf_fix_thread = CRLFFixThread(self.git_path, "quick")
        self.crlf_fix_thread.progress_updated.connect(self.log)
        self.crlf_fix_thread.fix_completed.connect(self.on_fix_completed)
        self.crlf_fix_thread.start()
        
        # 禁用按钮防止重复点击
        self.btn_quick_fix.setEnabled(False)
        self.btn_smart_fix.setEnabled(False)
    
    def on_fix_completed(self, success, message):
        """修复完成回调"""
        if success:
            self.log(f"✅ {message}")
        else:
            self.log(f"❌ {message}")
            QMessageBox.warning(self, "修复失败", message)
        
        # 重新启用按钮
        self.btn_quick_fix.setEnabled(True)
        self.btn_smart_fix.setEnabled(True)
    
    def show_crlf_error_dialog(self):
        """显示CRLF错误处理对话框"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Git换行符冲突")
        msg.setText("检测到Git换行符冲突！")
        msg.setInformativeText(
            "这是Windows/Unix换行符差异导致的。\n\n"
            "您可以选择以下解决方案："
        )
        
        # 添加自定义按钮
        btn_auto_fix = msg.addButton("自动修复", QMessageBox.AcceptRole)
        btn_manual = msg.addButton("查看指导", QMessageBox.HelpRole)
        btn_ignore = msg.addButton("暂时忽略", QMessageBox.RejectRole)
        
        msg.exec_()
        
        if msg.clickedButton() == btn_auto_fix:
            self.manual_quick_fix()
        elif msg.clickedButton() == btn_manual:
            self.show_manual_guidance()
    
    def show_manual_guidance(self):
        """显示手动处理指导"""
        guidance = """
CRLF问题手动解决指南：

方案1 - 临时解决：
在Git仓库中执行：
git config core.safecrlf false

方案2 - 永久解决：
创建.gitattributes文件，添加：
*.mesh binary
*.terraindata binary
*.cubemap binary

方案3 - 使用工具：
运行独立修复工具：
python crlf_auto_fix.py "仓库路径"
        """
        
        QMessageBox.information(self, "手动处理指导", guidance)
    
    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def main():
    """主程序"""
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = ArtResourceManagerWithCRLF()
    window.show()
    
    # 显示欢迎信息
    window.log("🎯 美术资源管理器已启动")
    window.log("✨ 已集成CRLF自动修复功能")
    window.log("💡 推送前会自动进行预防性修复")
    window.log("🔧 遇到CRLF问题时可自动处理")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 