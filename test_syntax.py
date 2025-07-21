class TestClass:
    def _add_guid_details(self, report_lines, issue, issue_type):
        """添加GUID相关问题的详细信息"""
        import re
        import json
        
        # 获取相关的GUID信息 - 兼容多种可能的字段名称
        print("函数正常运行") 