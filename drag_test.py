#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class TestDragDropWidget(QListWidget):
    """测试拖拽功能的简单组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)
        
        # 设置样式
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 5px;
                background-color: #f9f9f9;
                min-height: 200px;
            }
            QListWidget:hover {
                border-color: #0078d4;
                background-color: #f0f8ff;
            }
        """)
        
        # 添加提示
        self.addItem("拖拽任意文件或文件夹到此处")
    
    def dragEnterEvent(self, event):
        """拖拽进入"""
        print("拖拽进入事件触发")
        if event.mimeData().hasUrls():
            print("检测到URL数据")
            event.acceptProposedAction()
            self.setStyleSheet("""
                QListWidget {
                    border: 2px solid #0078d4;
                    border-radius: 5px;
                    background-color: #e6f3ff;
                    min-height: 200px;
                }
            """)
        else:
            print("没有URL数据")
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """拖拽离开"""
        print("拖拽离开事件触发")
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 5px;
                background-color: #f9f9f9;
                min_height: 200px;
            }
            QListWidget:hover {
                border-color: #0078d4;
                background-color: #f0f8ff;
            }
        """)
    
    def dropEvent(self, event):
        """拖拽放下"""
        print("拖拽放下事件触发")
        self.dragLeaveEvent(event)
        
        if event.mimeData().hasUrls():
            print(f"检测到 {len(event.mimeData().urls())} 个URL")
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    print(f"文件路径: {file_path}")
                    file_paths.append(file_path)
            
            if file_paths:
                self.process_dropped_files(file_paths)
                event.acceptProposedAction()
        else:
            event.ignore()
    
    def process_dropped_files(self, file_paths):
        """处理拖拽的文件"""
        self.clear()
        self.addItem(f"处理了 {len(file_paths)} 个文件/文件夹:")
        
        for file_path in file_paths:
            if os.path.isfile(file_path):
                self.addItem(f"文件: {file_path}")
            elif os.path.isdir(file_path):
                self.addItem(f"文件夹: {file_path}")
                # 递归遍历文件夹
                count = 0
                for root, dirs, files in os.walk(file_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        self.addItem(f"  └─ {full_path}")
                        count += 1
                        if count > 10:  # 限制显示数量
                            self.addItem(f"  └─ ... 还有更多文件")
                            break
                    if count > 10:
                        break

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("拖拽功能测试")
        self.setGeometry(100, 100, 600, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        layout.addWidget(QLabel("拖拽功能测试 - 请拖拽任意文件或文件夹到下方区域"))
        
        self.drag_widget = TestDragDropWidget()
        layout.addWidget(self.drag_widget)
        
        # 添加一个按钮来测试
        test_btn = QPushButton("测试按钮 - 点击查看当前目录")
        test_btn.clicked.connect(self.test_click)
        layout.addWidget(test_btn)
    
    def test_click(self):
        """测试按钮点击"""
        current_dir = os.getcwd()
        print(f"当前目录: {current_dir}")
        QMessageBox.information(self, "测试", f"当前目录: {current_dir}")

def main():
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    print("测试程序启动，请拖拽文件或文件夹到窗口中测试")
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 