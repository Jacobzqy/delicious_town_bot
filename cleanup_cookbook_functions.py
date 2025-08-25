#!/usr/bin/env python3
"""
清理cookbook_page.py中的好友兑换和特色菜礼包功能
"""

import re

def clean_cookbook_page():
    """清理cookbook_page.py"""
    file_path = "/Users/zhanqiuyang/PycharmProjects/delicious_town_bot/src/delicious_town_bot/plugins/clicker/cookbook_page.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 需要删除的import语句
    imports_to_remove = [
        r'from src\.delicious_town_bot\.actions\.shop import ShopAction\n',
        r'from src\.delicious_town_bot\.data\.specialty_food_packs import \(\n.*?\)\n',
    ]
    
    for pattern in imports_to_remove:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 需要删除的方法列表（按行号排序，从大到小删除）
    methods_to_remove = [
        '_create_friend_exchange_panel',
        '_create_specialty_pack_panel', 
        '_populate_specialty_packs',
        '_update_pack_info',
        '_buy_specialty_pack',
        '_buy_all_specialty_packs',
        '_on_pack_purchase_finished',
        '_on_batch_pack_purchase_finished',
        '_find_friends_with_target_food',
        '_manual_select_friends',
        '_start_friend_exchange',
        '_execute_manual_friend_exchange'
    ]
    
    # 删除每个方法的完整定义
    for method_name in methods_to_remove:
        # 匹配方法定义到下一个方法或类定义
        pattern = rf'    def {method_name}\(.*?\):\s*\n.*?(?=\n    def |\n    @|\nclass |\n    #|$)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 删除Worker类
    worker_classes = ['SpecialtyPackWorker', 'BatchSpecialtyPackWorker']
    for class_name in worker_classes:
        pattern = rf'class {class_name}\(.*?\):\s*\n.*?(?=\nclass |\n\n    def |$)'
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 删除FriendsSelectionDialog类（如果存在）
    pattern = r'class FriendsSelectionDialog\(.*?\):\s*\n.*?(?=\nclass |\n\n    def |$)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 清理多余的空行
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    # 保存清理后的文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ cookbook_page.py 清理完成")

if __name__ == "__main__":
    clean_cookbook_page()