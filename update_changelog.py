#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from datetime import datetime
from typing import List, Dict, Any

class ChangelogUpdater:
    """版本更新日志管理工具"""
    
    def __init__(self, changelog_file: str = "CHANGELOG.md"):
        self.changelog_file = changelog_file
        self.current_date = datetime.now().strftime("%Y年%m月%d日")
    
    def get_next_version(self) -> str:
        """获取下一个版本号"""
        if not os.path.exists(self.changelog_file):
            return "v0.0.1"
        
        try:
            with open(self.changelog_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找当前最新版本
            version_pattern = r'## v(\d+)\.(\d+)\.(\d+)'
            matches = re.findall(version_pattern, content)
            
            if not matches:
                return "v0.0.1"
            
            # 获取最高版本号
            latest_version = max(matches, key=lambda x: (int(x[0]), int(x[1]), int(x[2])))
            major, minor, patch = map(int, latest_version)
            
            # 默认增加patch版本
            return f"v{major}.{minor}.{patch + 1}"
            
        except Exception as e:
            print(f"❌ 获取版本号失败: {e}")
            return "v0.0.1"
    
    def add_new_version(self, version: str = None, features: List[str] = None, 
                       improvements: List[str] = None, fixes: List[str] = None,
                       custom_sections: Dict[str, List[str]] = None) -> bool:
        """添加新版本记录"""
        
        if version is None:
            version = self.get_next_version()
        
        # 构建新版本内容
        new_version_content = [
            f"## {version} - {self.current_date}",
            ""
        ]
        
        # 添加新增功能
        if features:
            new_version_content.extend([
                "### 🆕 新增功能",
                *[f"- {feature}" for feature in features],
                ""
            ])
        
        # 添加优化改进
        if improvements:
            new_version_content.extend([
                "### 🔧 优化改进",
                *[f"- {improvement}" for improvement in improvements],
                ""
            ])
        
        # 添加问题修复
        if fixes:
            new_version_content.extend([
                "### 🐛 问题修复",
                *[f"- {fix}" for fix in fixes],
                ""
            ])
        
        # 添加自定义章节
        if custom_sections:
            for section_title, section_items in custom_sections.items():
                new_version_content.extend([
                    f"### {section_title}",
                    *[f"- {item}" for item in section_items],
                    ""
                ])
        
        new_version_content.append("---")
        new_version_content.append("")
        
        return self._insert_new_version(new_version_content)
    
    def _insert_new_version(self, new_content: List[str]) -> bool:
        """将新版本内容插入到文件中"""
        try:
            if os.path.exists(self.changelog_file):
                with open(self.changelog_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                
                # 找到第一个版本记录的位置
                version_pattern = r'(## v\d+\.\d+\.\d+ - \d+年\d+月\d+日)'
                match = re.search(version_pattern, existing_content)
                
                if match:
                    # 在第一个版本前插入新版本
                    insert_pos = match.start()
                    new_changelog = (
                        existing_content[:insert_pos] + 
                        '\n'.join(new_content) + '\n' +
                        existing_content[insert_pos:]
                    )
                else:
                    # 如果没有找到版本记录，在文件末尾添加
                    new_changelog = existing_content + '\n' + '\n'.join(new_content)
            else:
                # 创建新文件
                header = [
                    "# 美术资源管理工具 - 更新日志",
                    "",
                    "## 版本说明",
                    "本文档记录了美术资源管理工具的所有版本更新内容，方便跟踪功能变化和问题修复。",
                    "",
                    "---",
                    ""
                ]
                new_changelog = '\n'.join(header + new_content)
            
            # 写入文件
            with open(self.changelog_file, 'w', encoding='utf-8') as f:
                f.write(new_changelog)
            
            return True
            
        except Exception as e:
            print(f"❌ 更新日志文件失败: {e}")
            return False
    
    def interactive_update(self):
        """交互式更新版本日志"""
        print("🚀 美术资源管理工具 - 版本日志更新器")
        print("=" * 50)
        
        # 获取版本号
        next_version = self.get_next_version()
        version = input(f"版本号 (默认: {next_version}): ").strip()
        if not version:
            version = next_version
        
        print(f"\n📝 添加版本 {version} - {self.current_date}")
        print("请输入更新内容 (每行一项，空行结束):")
        
        # 收集新增功能
        print("\n🆕 新增功能:")
        features = self._collect_items()
        
        # 收集优化改进
        print("\n🔧 优化改进:")
        improvements = self._collect_items()
        
        # 收集问题修复
        print("\n🐛 问题修复:")
        fixes = self._collect_items()
        
        # 执行更新
        if self.add_new_version(version, features, improvements, fixes):
            print(f"\n✅ 版本 {version} 已成功添加到更新日志！")
            print(f"📁 文件位置: {os.path.abspath(self.changelog_file)}")
        else:
            print("\n❌ 更新失败！")
    
    def _collect_items(self) -> List[str]:
        """收集用户输入的列表项"""
        items = []
        while True:
            item = input("  - ").strip()
            if not item:
                break
            items.append(item)
        return items

def main():
    """主函数"""
    updater = ChangelogUpdater()
    
    # 如果有命令行参数，使用非交互模式
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            # 快速添加示例更新
            features = ["示例新功能"]
            improvements = ["示例优化改进"]
            fixes = ["示例问题修复"]
            
            if updater.add_new_version(features=features, improvements=improvements, fixes=fixes):
                print("✅ 快速更新完成！")
            else:
                print("❌ 快速更新失败！")
        elif sys.argv[1] == "--help":
            print("使用方法:")
            print("  python update_changelog.py           # 交互式更新")
            print("  python update_changelog.py --quick   # 快速示例更新")
            print("  python update_changelog.py --help    # 显示帮助")
    else:
        # 交互式模式
        updater.interactive_update()

if __name__ == "__main__":
    main() 