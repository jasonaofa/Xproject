#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def fix_material_template_method():
    """完全修复材质模板检查方法"""
    
    # 读取文件
    with open('art_resource_manager.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到有问题的方法并替换
    lines = content.split('\n')
    
    # 找到方法的开始和结束位置
    start_line = -1
    end_line = -1
    
    for i, line in enumerate(lines):
        if 'def _check_material_templates(self) -> List[Dict[str, str]]:' in line:
            start_line = i
        elif start_line != -1 and line.strip() and not line.startswith('    ') and not line.startswith('\t'):
            end_line = i
            break
    
    # 如果没有找到结束位置，查找下一个方法
    if end_line == -1:
        for i in range(start_line + 1, len(lines)):
            if lines[i].strip() and lines[i].startswith('    def '):
                end_line = i
                break
    
    if start_line == -1:
        print("没有找到方法开始位置")
        return
    
    # 创建新的方法内容
    new_method = '''    def _check_material_templates(self) -> List[Dict[str, str]]:
        """检查材质模板使用情况"""
        issues = []
        
        # 允许的材质模板列表
        allowed_templates = {
            'Character_NPR_Opaque.templatemat',
            'Character_NPR_Masked.templatemat',
            'Character_NPR_Tranclucent.templatemat',
            'Character_AVATAR_Masked.templatemat',
            'Character_AVATAR_Opaque.templatemat',
            'Character_AVATAR_Tranclucent.templatemat',
            'Character_PBR_Opaque.templatemat',
            'Character_PBR_Translucent.templatemat',
            'Scene_Prop_Opaque.templatemat',
            'Scene_Prop_Tranclucent.templatemat',
            'Scene_Prop_Masked.templatemat',
            'Sight.templatemat'
        }
        
        try:
            self.status_updated.emit("🔍 开始材质模板检查...")
            
            # 筛选出需要检查的材质文件
            material_files = []
            for file_path in self.upload_files:
                if not file_path.lower().endswith('.mat'):
                    continue
                
                # 检查是否在entity目录下
                normalized_path = os.path.normpath(file_path)
                path_parts = normalized_path.split(os.sep)
                
                # 查找entity目录
                entity_index = -1
                for i, part in enumerate(path_parts):
                    if part.lower() == 'entity':
                        entity_index = i
                        break
                
                if entity_index == -1:
                    continue  # 不在entity目录下，跳过
                
                # 检查是否在排除的目录中
                excluded_path = False
                remaining_parts = path_parts[entity_index + 1:]
                
                # 检查是否在entity/Environment/Scenes目录下
                if (len(remaining_parts) >= 2 and 
                    remaining_parts[0].lower() == 'environment' and 
                    remaining_parts[1].lower() == 'scenes'):
                    excluded_path = True
                
                if not excluded_path:
                    material_files.append(file_path)
            
            self.status_updated.emit(f"找到 {len(material_files)} 个需要检查的材质文件")
            
            # 检查每个材质文件的模板使用情况
            for file_path in material_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 查找模板引用
                    template_references = self._find_template_references(content)
                    
                    if not template_references:
                        # 没有找到模板引用，这可能是问题
                        issues.append({
                            'file': file_path,
                            'type': 'no_template_found',
                            'message': '未找到材质模板引用'
                        })
                    else:
                        # 检查使用的模板是否在允许列表中
                        found_valid_template = False
                        for template_name in template_references:
                            # 跳过GUID引用，这些不是实际的模板名称
                            if template_name.startswith('TEMPLATE_GUID:'):
                                continue
                            
                            if template_name in allowed_templates:
                                # 记录使用了正确的模板（信息性）
                                self.status_updated.emit(f"✅ {os.path.basename(file_path)} 使用了正确模板: {template_name}")
                                found_valid_template = True
                            else:
                                issues.append({
                                    'file': file_path,
                                    'type': 'invalid_template',
                                    'message': f'使用了不允许的材质模板: {template_name}',
                                    'template_name': template_name
                                })
                        
                        # 如果只找到了GUID引用而没有找到实际的模板名称，视为没有模板
                        if not found_valid_template and all(ref.startswith('TEMPLATE_GUID:') for ref in template_references):
                            issues.append({
                                'file': file_path,
                                'type': 'no_template_found',
                                'message': '未找到材质模板引用（仅找到GUID引用）'
                            })
                    
                except Exception as e:
                    issues.append({
                        'file': file_path,
                        'type': 'template_check_error',
                        'message': f'材质模板检查失败: {str(e)}'
                    })
            
            if issues:
                blocking_issues = [issue for issue in issues if issue.get('type') != 'no_template_found']
                if blocking_issues:
                    self.status_updated.emit(f"材质模板检查完成，发现 {len(blocking_issues)} 个问题")
                else:
                    self.status_updated.emit(f"材质模板检查完成，发现 {len(issues)} 个警告")
            else:
                self.status_updated.emit("✅ 材质模板检查通过，所有材质都使用了正确的模板")
                
        except Exception as e:
            issues.append({
                'file': 'SYSTEM',
                'type': 'template_check_system_error',
                'message': f'材质模板检查系统错误: {str(e)}'
            })
        
        return issues
'''.split('\n')
    
    # 替换有问题的方法
    if end_line == -1:
        end_line = len(lines)
    
    new_lines = lines[:start_line] + new_method + lines[end_line:]
    
    # 写回文件
    with open('art_resource_manager.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"方法修复完成，替换了第 {start_line} 到第 {end_line} 行")

if __name__ == "__main__":
    fix_material_template_method() 