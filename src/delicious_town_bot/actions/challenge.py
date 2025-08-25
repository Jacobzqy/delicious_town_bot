import json
import os
import re
import time
from typing import Any, Dict, Optional, Tuple

from delicious_town_bot.constants import (
    MissileType, MonsterAttackItem,
    SHRINE_MONSTER_ATTRIBUTE_MAP, ELEMENT_NAME_TO_MISSILE_MAP,
    get_counter_element_name
)
from delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class ChallengeAction(BaseAction):
    """
    封装与挑战相关的操作，实现了厨塔和神殿（守卫、怪兽）功能。
    """

    # 厨塔层级 (Level) 到请求 ID 的映射
    TOWER_LEVEL_TO_ID_MAP = {
        1: 4, 2: 5, 3: 6,
        4: 1, 5: 2, 6: 3,
        7: 7, 8: 8, 9: 9,
    }

    def __init__(self, key: str, cookie: Optional[Dict[str, str]] = None):
        base_url = "http://117.72.123.195/index.php?g=Res"
        super().__init__(key=key, cookie=cookie, base_url=base_url)
        # 更新 Referer 以适应多个挑战页面，指向基础域名通常是安全的
        self.http_client.headers.update({
            'Referer': 'http://117.72.123.195/'
        })

    # ==========================================================================
    # 厨塔 (Tower) 相关方法
    # ==========================================================================

    def _parse_tower_attack_response(self, msg: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        【修正版】私有辅助方法：解析厨塔挑战结果的 msg 字符串，提取奖励和比分。
        """
        rewards = {}
        
        # 提取比分信息 - 查找"总比分"行
        score_match = re.search(r"总比分[：:](\d+(?:\.\d+)?)[：:](\d+(?:\.\d+)?)", msg)
        if score_match:
            user_power = float(score_match.group(1))
            opponent_power = float(score_match.group(2))
            rewards['score'] = {'user_power': user_power, 'opponent_power': opponent_power}

        # 1. 判断成功或失败，并提取概要信息
        if "挑战失败哦" in msg:
            is_success, summary = False, msg.split('<br>')[0]
        elif "恭喜您打败了" in msg:
            is_success, summary = True, msg.split('<br>')[0]
        else:
            # 未知状态
            return False, f"未知的挑战结果: {msg[:50]}...", {}

        # 2. 提取声望变化（成功和失败都可能有）
        reputation_match = re.search(r"声望([+-]\d+)", msg)
        if reputation_match:
            reputation_change = int(reputation_match.group(1))
            if is_success:
                rewards['reputation'] = reputation_change
            else:
                # 失败时记录为处罚
                rewards['penalty'] = {'reputation': abs(reputation_change)}
                # 但仍保留原格式以兼容现有代码
                rewards['reputation'] = reputation_change

        # 如果挑战失败，返回包含处罚信息的结果
        if not is_success:
            return is_success, summary, rewards

        # 3. 如果挑战成功，使用正则表达式逐一提取所有奖励（声望已在上面处理过了）

        # 金币
        gold_match = re.search(r"金币:(\d+)", msg)
        if gold_match:
            rewards['gold'] = int(gold_match.group(1))

        # 经验
        exp_match = re.search(r"经验:(\d+)", msg)
        if exp_match:
            rewards['experience'] = int(exp_match.group(1))

        # 3. 【核心修正】提取所有物品和食材
        # 这个新的正则表达式会查找所有 "获得物品:" 或 "获得食材:" 后面的 "名称x数量" 格式
        # 它会正确处理像 "小仙的策划黑锅" 这样复杂的名称
        items = {}
        # re.findall 会找到所有匹配项，返回一个元组列表 [('名称1', '数量1'), ('名称2', '数量2'), ...]
        all_item_matches = re.findall(r"获得(?:物品|食材):([\w\u4e00-\u9fa5·]+)x(\d+)", msg)

        for name, quantity in all_item_matches:
            # .strip() 用于去除可能存在的多余空格
            items[name.strip()] = items.get(name.strip(), 0) + int(quantity)

        if items:
            rewards['items'] = items

        return is_success, summary, rewards

    def attack_tower(self, level: int) -> Dict[str, Any]:
        """挑战厨塔的指定层级。"""
        print(f"[*] 正在尝试挑战厨塔第 {level} 层...")
        if level not in self.TOWER_LEVEL_TO_ID_MAP:
            error_msg = f"无效的厨塔层级: {level}。有效范围是 1-9。"
            print(f"[Error] {error_msg}")
            return {"success": False, "message": error_msg, "rewards": {}}

        tower_id = self.TOWER_LEVEL_TO_ID_MAP[level]
        action_path = "m=Tower&a=attack"
        payload = {"id": str(tower_id)}

        try:
            response_data = self.post(action_path, data=payload)

            msg = response_data.get('msg', '')
            is_success, summary, rewards = self._parse_tower_attack_response(msg)

            result = {"success": is_success, "message": summary, "rewards": rewards}
            if is_success:
                print(f"[+] 挑战成功: {summary}")
            else:
                print(f"[!] 挑战失败: {summary}")

            return result
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 挑战厨塔失败: {e}")
            return {"success": False, "message": str(e), "rewards": {}}

    # ==========================================================================
    # 神殿守卫 (Shrine Guard) 相关方法
    # ==========================================================================

    def get_shrine_info(self) -> Dict[str, Any]:
        """获取神殿守卫的详细信息和普通飞弹数量。"""
        print("[*] 正在获取神殿守卫信息...")
        action_path = "m=Shrine&a=get_info"
        try:
            response = self.post(action_path)
            shrine_data = response.get('data', {})
            print("[+] 成功获取神殿守卫信息。")
            return {"success": True, "data": shrine_data}
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 获取神殿守卫信息失败: {e}")
            return {"success": False, "data": None, "message": str(e)}

    def _parse_shrine_attack_msg(self, msg: str) -> Dict[str, Any]:
        """解析神殿守卫攻击成功后的消息，提取伤害和消耗。"""
        result = {}
        damage_match = re.search(r"-(\d+)hp", msg)
        if damage_match: result['damage'] = int(damage_match.group(1))

        cost_match = re.search(r"(.+?)\*-(\d+)", msg)
        if cost_match:
            result['missile_used'] = cost_match.group(1)
            result['cost'] = int(cost_match.group(2))
        return result

    def attack_shrine_guard(self, missile_type: MissileType) -> Dict[str, Any]:
        """使用指定类型的飞弹攻击神殿守卫。"""
        print(f"[*] 正在尝试使用 '{missile_type.name}' 飞弹攻击神殿守卫...")
        action_path = "m=Shrine&a=attack"
        payload = {"code": missile_type.value}
        try:
            response = self.post(action_path, data=payload)
            msg = response.get('msg', '操作成功，但无消息返回。')
            parsed_result = self._parse_shrine_attack_msg(msg)
            print(f"[+] 攻击成功: {msg.replace('<br>', ' ')}")
            return {"success": True, "message": msg, "result": parsed_result}
        except BusinessLogicError as e:
            print(f"[!] 操作失败 (业务逻辑): {e}")
            return {"success": False, "message": str(e), "result": None}
        except (ConnectionError, Exception) as e:
            print(f"[Error] 攻击神殿守卫失败 (网络或未知错误): {e}")
            return {"success": False, "message": str(e), "result": None}

    # ==========================================================================
    # 神殿怪兽 (Shrine Monster) 相关方法
    # ==========================================================================

    def get_shrine_monster_info(self) -> Dict[str, Any]:
        """获取神殿怪兽的详细信息，包括其状态和你的元素飞弹库存。"""
        print("[*] 正在获取神殿怪兽信息...")
        action_path = "m=Shrine&a=get_monster_info"
        try:
            response = self.post(action_path)
            monster_info_data = response.get('data', {})
            print("[+] 成功获取神殿怪兽信息。")
            return {"success": True, "data": monster_info_data}
        except (BusinessLogicError, ConnectionError, Exception) as e:
            print(f"[Error] 获取神殿怪兽信息失败: {e}")
            return {"success": False, "data": None, "message": str(e)}

    def recommend_monster_missile(self, monster_info: Dict[str, Any]) -> Optional[MonsterAttackItem]:
        """根据获取到的怪兽信息和飞弹库存，推荐最佳攻击飞弹。"""
        monster_data = monster_info.get("monster_data", {})
        missile_list = monster_info.get("missile_list", [])

        attribute_id = monster_data.get("attribute")
        if not isinstance(attribute_id, int) or attribute_id not in SHRINE_MONSTER_ATTRIBUTE_MAP:
            print("[Info] 怪兽信息中无有效元素属性，无法推荐克制飞弹。")
            return None

        monster_element = SHRINE_MONSTER_ATTRIBUTE_MAP[attribute_id]
        counter_element = get_counter_element_name(monster_element)
        print(f"[Info] 怪兽元素: '{monster_element}' -> 推荐使用克制元素: '{counter_element}'")

        available_missiles = {
            missile['goods_name'].split('·')[-1]: missile['num']
            for missile in missile_list if isinstance(missile.get('num'), (str, int)) and int(missile['num']) > 0
        }

        if counter_element in available_missiles:
            print(f"[+] 发现可用克制飞弹 '{counter_element}'，数量: {available_missiles[counter_element]}。")
            return ELEMENT_NAME_TO_MISSILE_MAP.get(counter_element)
        else:
            print(f"[Warn] 无可用的 '{counter_element}' 飞弹。正在检查'意'飞弹...")
            if "意" in available_missiles:
                print(f"[+] 发现可用'意'飞弹，数量: {available_missiles['意']}。")
                return MonsterAttackItem.YI

        print("[Error] 无任何可用飞弹（克制弹或'意'弹均无）。")
        return None

    def attack_shrine_monster(self, item: MonsterAttackItem) -> Dict[str, Any]:
        """使用指定物品攻击神殿怪兽。"""
        print(f"[*] 正在尝试使用 '{item.name}' ({item.value}) 攻击神殿怪兽...")
        action_path = "m=Shrine&a=attackMonster"
        payload = {"code": item.value}
        try:
            response = self.post(action_path, data=payload)
            msg = response.get('msg', '操作成功，但无消息返回。')
            print(f"[+] 攻击请求已发送: {msg}")
            return {"success": True, "message": msg}
        except BusinessLogicError as e:
            print(f"[!] 操作失败: {e}")
            return {"success": False, "message": str(e)}
        except (ConnectionError, Exception) as e:
            print(f"[Error] 攻击怪兽失败 (网络或未知错误): {e}")
            return {"success": False, "message": str(e)}


# ==============================================================================
#  独立测试脚本 (Standalone Test Script)
# ==============================================================================
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    TEST_KEY = os.getenv("TEST_KEY")
    TEST_COOKIE_STR = os.getenv("TEST_COOKIE")
    if not TEST_KEY or not TEST_COOKIE_STR:
        raise ValueError("请在 .env 文件中设置 TEST_KEY 和 TEST_COOKIE")
    TEST_COOKIE_DICT = {"PHPSESSID": TEST_COOKIE_STR}

    challenge_action = ChallengeAction(key=TEST_KEY, cookie=TEST_COOKIE_DICT)

    print("\n" + "=" * 20 + " 全面挑战功能测试 " + "=" * 20)

    # --- 1. 厨塔测试 ---
    print("\n--- 1. 厨塔功能测试 ---")
    result = challenge_action.attack_tower(level=6)
    print(f"[*] 任务完成，获取到的结果: {result}")
    time.sleep(1)


    # --- 2. 神殿守卫测试 ---
    print("\n--- 2. 神殿守卫功能测试 ---")
    guard_info_res = challenge_action.get_shrine_info()
    if guard_info_res["success"]:
        print("成功获取守卫信息，尝试使用常规飞弹攻击...")
        challenge_action.attack_shrine_guard(MissileType.REGULAR)
    time.sleep(1)

    # --- 3. 神殿怪兽测试 ---
    print("\n--- 3. 神殿怪兽完整流程测试 ---")
    # 步骤 3.1: 获取信息
    print("\n--- 步骤 3.1: 获取怪兽信息和飞弹库存 ---")
    monster_info_res = challenge_action.get_shrine_monster_info()
    if not monster_info_res["success"]:
        print("\n--- 测试因信息获取失败而中止 ---")
    else:
        monster_info_data = monster_info_res["data"]

        monster_hp = monster_info_data.get("monster_data", {}).get("hp")
        if monster_hp and monster_hp != "false":
            print(f"怪兽当前 HP: {monster_hp}")
        else:
            print("怪兽当前未出现或已被击败。")

        # 步骤 3.2: 推荐飞弹
        print("\n--- 步骤 3.2: 根据信息推荐飞弹 ---")
        recommended_missile = challenge_action.recommend_monster_missile(monster_info_data)

        # 步骤 3.3: 执行攻击
        print("\n--- 步骤 3.3: 使用推荐的飞弹进行攻击 ---")
        if recommended_missile:
            print(f"系统推荐使用: {recommended_missile.name} (Code: {recommended_missile.value})")
            challenge_action.attack_shrine_monster(recommended_missile)
        else:
            print("未推荐任何飞弹，跳过攻击步骤。")

    print("\n" + "=" * 20 + " 所有测试执行完毕 " + "=" * 20)