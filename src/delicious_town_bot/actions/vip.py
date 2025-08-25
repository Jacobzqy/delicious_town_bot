"""
VIP管理相关操作
包括VIP购买、CDK兑换等功能，支持单个账号和批量操作
"""
import logging
from typing import Dict, Any, Optional, List
from src.delicious_town_bot.actions.base_action import BaseAction, BusinessLogicError


class VipAction(BaseAction):
    """VIP管理操作类"""
    
    def __init__(self, key: str, cookie: Optional[Dict[str, str]]):
        """初始化VIP管理操作实例"""
        self.cdk_base_url = "http://117.72.123.195/index.php?g=Res&m=Cdk"
        super().__init__(key=key, base_url=self.cdk_base_url, cookie=cookie)
    
    def exchange_cdk(self, cdk_code: str) -> Dict[str, Any]:
        """
        兑换CDK码
        
        Args:
            cdk_code: CDK兑换码
            
        Returns:
            Dict[str, Any]: 兑换结果
        """
        try:
            logging.info(f"开始兑换CDK码: {cdk_code}")
            
            response = self.post(
                action_path="a=cdk",
                data={
                    "cdk": cdk_code
                }
            )
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            data = response.get("data", {})
            
            if success:
                logging.info(f"CDK兑换成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "data": data,
                    "raw_response": response
                }
            else:
                logging.warning(f"CDK兑换失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "data": data,
                    "raw_response": response
                }
                
        except BusinessLogicError as e:
            logging.error(f"CDK兑换业务逻辑错误: {e}")
            return {
                "success": False,
                "message": f"兑换失败: {e}",
                "data": {},
                "raw_response": {}
            }
        except Exception as e:
            logging.error(f"CDK兑换异常: {e}")
            return {
                "success": False,
                "message": f"兑换异常: {e}",
                "data": {},
                "raw_response": {}
            }
    
    def get_vip_info(self) -> Dict[str, Any]:
        """
        获取VIP信息
        
        Returns:
            Dict[str, Any]: VIP信息
        """
        try:
            logging.info("获取VIP信息")
            
            response = self.post(
                action_path="g=Res&m=Vip&a=getVipInfo",
                data={
                    "key": self.key
                }
            )
            
            success = response.get("status", False)
            message = response.get("msg", "")
            data = response.get("data", {})
            
            if success:
                # 解析VIP信息
                vip_list = data.get("vipList", [])
                res_info = data.get("resInfo", {})
                user_info = data.get("userInfo", {})
                
                # 提取关键VIP信息
                vip_level = res_info.get("vip_level", "0")
                vip_time = res_info.get("vip_time", "")
                restaurant_name = res_info.get("name", "")
                level = res_info.get("level", "0")
                gold = res_info.get("gold", "0")
                
                logging.info(f"VIP信息获取成功: VIP等级{vip_level}, 到期时间{vip_time}")
                return {
                    "success": True,
                    "message": message or "VIP信息获取成功",
                    "vip_info": {
                        "vip_level": vip_level,
                        "vip_time": vip_time,
                        "restaurant_name": restaurant_name,
                        "level": level,
                        "gold": gold,
                        "vip_privileges": vip_list,
                        "restaurant_info": res_info,
                        "user_info": user_info
                    },
                    "raw_response": response
                }
            else:
                logging.warning(f"VIP信息获取失败: {message}")
                return {
                    "success": False,
                    "message": message or "获取VIP信息失败",
                    "vip_info": {},
                    "raw_response": response
                }
                
        except Exception as e:
            logging.error(f"获取VIP信息异常: {e}")
            return {
                "success": False,
                "message": f"获取失败: {e}",
                "vip_info": {},
                "raw_response": {}
            }
    
    def purchase_vip(self, cost_diamonds: int = 120) -> Dict[str, Any]:
        """
        购买VIP（使用钻石）
        
        Args:
            cost_diamonds: VIP购买费用（钻石数量，默认120钻石）
            
        Returns:
            Dict[str, Any]: 购买结果
        """
        try:
            logging.info(f"开始购买VIP，费用: {cost_diamonds} 钻石")
            
            response = self.post(
                action_path="g=Res&m=Vip&a=buyVip",
                data={
                    "key": self.key
                }
            )
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            purchase_data = response.get("data", {})
            
            if success:
                logging.info(f"VIP购买成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "purchase_info": purchase_data,
                    "cost_diamonds": cost_diamonds,
                    "raw_response": response
                }
            else:
                logging.warning(f"VIP购买失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "purchase_info": purchase_data,
                    "cost_diamonds": cost_diamonds,
                    "raw_response": response
                }
                
        except Exception as e:
            logging.error(f"VIP购买异常: {e}")
            return {
                "success": False,
                "message": f"购买失败: {e}",
                "purchase_info": {},
                "raw_response": {}
            }
    
    def get_vip_packages(self) -> Dict[str, Any]:
        """
        获取VIP套餐列表
        
        Returns:
            Dict[str, Any]: VIP套餐信息
        """
        try:
            logging.info("获取VIP套餐列表")
            
            # 这里需要确定获取VIP套餐的具体API端点
            # 暂时使用占位符，后续需要根据实际API调整
            url = "http://117.72.123.195/index.php?g=Res&m=Vip&a=packages"
            data = {
                "key": self.key
            }
            
            response_raw = self.http_client.post(url, data=data, timeout=self.timeout)
            response_raw.raise_for_status()
            response = response_raw.json()
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            packages_data = response.get("data", [])
            
            if success:
                logging.info(f"VIP套餐获取成功")
                return {
                    "success": True,
                    "message": message,
                    "packages": packages_data,
                    "raw_response": response
                }
            else:
                logging.warning(f"VIP套餐获取失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "packages": [],
                    "raw_response": response
                }
                
        except Exception as e:
            logging.error(f"获取VIP套餐异常: {e}")
            return {
                "success": False,
                "message": f"获取失败: {e}",
                "packages": [],
                "raw_response": {}
            }
    
    def batch_exchange_cdk(self, accounts: List[Dict[str, Any]], cdk_code: str) -> Dict[str, Any]:
        """
        批量兑换CDK码
        
        Args:
            accounts: 账户列表，格式: [{"key": "密钥", "cookie": {"PHPSESSID": "会话"}, "username": "用户名"}, ...]
            cdk_code: CDK兑换码
            
        Returns:
            Dict[str, Any]: 批量兑换结果
        """
        try:
            logging.info(f"开始批量兑换CDK码: {cdk_code}，涉及 {len(accounts)} 个账户")
            
            results = []
            success_count = 0
            failure_count = 0
            
            for i, account in enumerate(accounts, 1):
                username = account.get("username", f"账户{i}")
                key = account.get("key", "")
                cookie = account.get("cookie", {})
                
                logging.info(f"[{i}/{len(accounts)}] 为账户 {username} 兑换CDK")
                
                # 创建临时VIP操作实例
                temp_vip_action = VipAction(key, cookie)
                result = temp_vip_action.exchange_cdk(cdk_code)
                
                # 添加账户信息到结果
                result["account"] = {
                    "username": username,
                    "key": key,
                    "index": i
                }
                
                results.append(result)
                
                if result.get("success", False):
                    success_count += 1
                    logging.info(f"账户 {username} CDK兑换成功")
                else:
                    failure_count += 1
                    logging.warning(f"账户 {username} CDK兑换失败: {result.get('message', '未知错误')}")
            
            logging.info(f"批量CDK兑换完成: 成功 {success_count} 个, 失败 {failure_count} 个")
            
            return {
                "success": True,
                "message": f"批量兑换完成: 成功 {success_count}/{len(accounts)} 个账户",
                "total_accounts": len(accounts),
                "success_count": success_count,
                "failure_count": failure_count,
                "results": results,
                "cdk_code": cdk_code
            }
            
        except Exception as e:
            logging.error(f"批量CDK兑换异常: {e}")
            return {
                "success": False,
                "message": f"批量兑换异常: {e}",
                "total_accounts": len(accounts) if accounts else 0,
                "success_count": 0,
                "failure_count": 0,
                "results": [],
                "cdk_code": cdk_code
            }
    
    def batch_purchase_vip(self, accounts: List[Dict[str, Any]], cost_diamonds: int = 120) -> Dict[str, Any]:
        """
        批量购买VIP
        
        Args:
            accounts: 账户列表
            cost_diamonds: VIP购买费用（钻石数量，默认120钻石）
            
        Returns:
            Dict[str, Any]: 批量购买结果
        """
        try:
            logging.info(f"开始批量购买VIP，费用: {cost_diamonds} 钻石，涉及 {len(accounts)} 个账户")
            
            results = []
            success_count = 0
            failure_count = 0
            
            for i, account in enumerate(accounts, 1):
                username = account.get("username", f"账户{i}")
                key = account.get("key", "")
                cookie = account.get("cookie", {})
                
                logging.info(f"[{i}/{len(accounts)}] 为账户 {username} 购买VIP")
                
                # 创建临时VIP操作实例
                temp_vip_action = VipAction(key, cookie)
                result = temp_vip_action.purchase_vip(cost_diamonds)
                
                # 添加账户信息到结果
                result["account"] = {
                    "username": username,
                    "key": key,
                    "index": i
                }
                
                results.append(result)
                
                if result.get("success", False):
                    success_count += 1
                    logging.info(f"账户 {username} VIP购买成功")
                else:
                    failure_count += 1
                    logging.warning(f"账户 {username} VIP购买失败: {result.get('message', '未知错误')}")
            
            logging.info(f"批量VIP购买完成: 成功 {success_count} 个, 失败 {failure_count} 个")
            
            return {
                "success": True,
                "message": f"批量购买完成: 成功 {success_count}/{len(accounts)} 个账户",
                "total_accounts": len(accounts),
                "success_count": success_count,
                "failure_count": failure_count,
                "results": results,
                "cost_diamonds": cost_diamonds
            }
            
        except Exception as e:
            logging.error(f"批量VIP购买异常: {e}")
            return {
                "success": False,
                "message": f"批量购买异常: {e}",
                "total_accounts": len(accounts) if accounts else 0,
                "success_count": 0,
                "failure_count": 0,
                "results": [],
                "cost_diamonds": cost_diamonds
            }
    
    def batch_get_vip_info(self, accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量获取VIP信息
        
        Args:
            accounts: 账户列表
            
        Returns:
            Dict[str, Any]: 批量VIP信息结果
        """
        try:
            logging.info(f"开始批量获取VIP信息，涉及 {len(accounts)} 个账户")
            
            results = []
            success_count = 0
            failure_count = 0
            
            for i, account in enumerate(accounts, 1):
                username = account.get("username", f"账户{i}")
                key = account.get("key", "")
                cookie = account.get("cookie", {})
                
                logging.info(f"[{i}/{len(accounts)}] 获取账户 {username} VIP信息")
                
                # 创建临时VIP操作实例
                temp_vip_action = VipAction(key, cookie)
                result = temp_vip_action.get_vip_info()
                
                # 添加账户信息到结果
                result["account"] = {
                    "username": username,
                    "key": key,
                    "index": i
                }
                
                results.append(result)
                
                if result.get("success", False):
                    success_count += 1
                    logging.info(f"账户 {username} VIP信息获取成功")
                else:
                    failure_count += 1
                    logging.warning(f"账户 {username} VIP信息获取失败: {result.get('message', '未知错误')}")
            
            logging.info(f"批量VIP信息获取完成: 成功 {success_count} 个, 失败 {failure_count} 个")
            
            return {
                "success": True,
                "message": f"批量获取完成: 成功 {success_count}/{len(accounts)} 个账户",
                "total_accounts": len(accounts),
                "success_count": success_count,
                "failure_count": failure_count,
                "results": results
            }
            
        except Exception as e:
            logging.error(f"批量VIP信息获取异常: {e}")
            return {
                "success": False,
                "message": f"批量获取异常: {e}",
                "total_accounts": len(accounts) if accounts else 0,
                "success_count": 0,
                "failure_count": 0,
                "results": []
            }
    
    def batch_vip_shop_exchange(self, accounts: List[Dict[str, Any]], item_id: str, quantity: int = 1) -> Dict[str, Any]:
        """
        批量VIP商店兑换（预留接口）
        
        Args:
            accounts: 账户列表
            item_id: 商品ID
            quantity: 兑换数量
            
        Returns:
            Dict[str, Any]: 批量兑换结果
        """
        try:
            logging.info(f"开始批量VIP商店兑换: 商品ID {item_id}，数量 {quantity}，涉及 {len(accounts)} 个账户")
            
            results = []
            success_count = 0
            failure_count = 0
            
            for i, account in enumerate(accounts, 1):
                username = account.get("username", f"账户{i}")
                key = account.get("key", "")
                cookie = account.get("cookie", {})
                
                logging.info(f"[{i}/{len(accounts)}] 为账户 {username} 进行VIP商店兑换")
                
                # 模拟VIP商店兑换API调用（预留实现）
                try:
                    # 这里将来集成真实的VIP商店兑换API
                    # temp_vip_action = VipAction(key, cookie)
                    # result = temp_vip_action.vip_shop_exchange(item_id, quantity)
                    
                    # 当前为模拟实现
                    result = {
                        "success": True,
                        "message": f"VIP商店兑换成功: 商品ID {item_id} x{quantity}",
                        "data": {
                            "item_id": item_id,
                            "quantity": quantity,
                            "item_name": f"VIP商品{item_id}"
                        }
                    }
                    
                except Exception as e:
                    result = {
                        "success": False,
                        "message": f"VIP商店兑换失败: {e}",
                        "data": {}
                    }
                
                # 添加账户信息到结果
                result["account"] = {
                    "username": username,
                    "key": key,
                    "index": i
                }
                
                results.append(result)
                
                if result.get("success", False):
                    success_count += 1
                    logging.info(f"账户 {username} VIP商店兑换成功")
                else:
                    failure_count += 1
                    logging.warning(f"账户 {username} VIP商店兑换失败: {result.get('message', '未知错误')}")
            
            logging.info(f"批量VIP商店兑换完成: 成功 {success_count} 个, 失败 {failure_count} 个")
            
            return {
                "success": True,
                "message": f"批量兑换完成: 成功 {success_count}/{len(accounts)} 个账户",
                "total_accounts": len(accounts),
                "success_count": success_count,
                "failure_count": failure_count,
                "results": results,
                "item_id": item_id,
                "quantity": quantity
            }
            
        except Exception as e:
            logging.error(f"批量VIP商店兑换异常: {e}")
            return {
                "success": False,
                "message": f"批量兑换异常: {e}",
                "total_accounts": len(accounts) if accounts else 0,
                "success_count": 0,
                "failure_count": 0,
                "results": [],
                "item_id": item_id,
                "quantity": quantity
            }
    
    def open_gift_package(self, package_code: str) -> Dict[str, Any]:
        """
        打开礼包
        
        Args:
            package_code: 礼包代码
            
        Returns:
            Dict[str, Any]: 打开结果
        """
        try:
            logging.info(f"开始打开礼包，代码: {package_code}")
            
            # 使用仓库使用物品API
            url = "http://117.72.123.195/index.php?g=Res&m=Depot&a=use_step_1"
            data = {
                "key": self.key,
                "code": package_code
            }
            
            response_raw = self.http_client.post(url, data=data, timeout=self.timeout)
            response_raw.raise_for_status()
            response = response_raw.json()
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            response_data = response.get("data", [])
            
            if success:
                logging.info(f"礼包打开成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "data": response_data,
                    "raw_response": response
                }
            else:
                logging.warning(f"礼包打开失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "data": response_data,
                    "raw_response": response
                }
                
        except BusinessLogicError as e:
            logging.error(f"礼包打开业务逻辑错误: {e}")
            return {
                "success": False,
                "message": f"打开失败: {e}",
                "data": [],
                "raw_response": {}
            }
        except Exception as e:
            logging.error(f"礼包打开异常: {e}")
            return {
                "success": False,
                "message": f"打开异常: {e}",
                "data": [],
                "raw_response": {}
            }
    
    def batch_open_gift_packages(self, accounts: List[Dict[str, Any]], package_codes: List[str]) -> Dict[str, Any]:
        """
        批量打开礼包
        
        Args:
            accounts: 账户列表
            package_codes: 礼包代码列表
            
        Returns:
            Dict[str, Any]: 批量打开结果
        """
        try:
            logging.info(f"开始批量打开礼包: {len(package_codes)} 种礼包，涉及 {len(accounts)} 个账户")
            
            results = []
            total_operations = len(accounts) * len(package_codes)
            success_count = 0
            failure_count = 0
            
            for i, account in enumerate(accounts, 1):
                username = account.get("username", f"账户{i}")
                key = account.get("key", "")
                cookie = account.get("cookie", {})
                
                logging.info(f"[{i}/{len(accounts)}] 为账户 {username} 打开礼包")
                
                account_results = []
                account_success = 0
                account_failure = 0
                
                # 创建临时VIP操作实例
                temp_vip_action = VipAction(key, cookie)
                
                for j, package_code in enumerate(package_codes, 1):
                    logging.info(f"  [{j}/{len(package_codes)}] 打开礼包: {package_code}")
                    
                    result = temp_vip_action.open_gift_package(package_code)
                    
                    # 添加礼包信息到结果
                    result["package_code"] = package_code
                    result["package_index"] = j
                    
                    account_results.append(result)
                    
                    if result.get("success", False):
                        account_success += 1
                        success_count += 1
                        logging.info(f"    ✅ 礼包 {package_code} 打开成功")
                    else:
                        account_failure += 1
                        failure_count += 1
                        logging.warning(f"    ❌ 礼包 {package_code} 打开失败: {result.get('message', '未知错误')}")
                
                # 账户结果汇总
                account_result = {
                    "account": {
                        "username": username,
                        "key": key,
                        "index": i
                    },
                    "total_packages": len(package_codes),
                    "success_count": account_success,
                    "failure_count": account_failure,
                    "package_results": account_results
                }
                
                results.append(account_result)
                logging.info(f"账户 {username} 礼包打开完成: 成功 {account_success}/{len(package_codes)} 个")
            
            logging.info(f"批量礼包打开完成: 成功 {success_count}/{total_operations} 个操作")
            
            return {
                "success": True,
                "message": f"批量打开完成: 成功 {success_count}/{total_operations} 个操作",
                "total_accounts": len(accounts),
                "total_packages": len(package_codes),
                "total_operations": total_operations,
                "success_count": success_count,
                "failure_count": failure_count,
                "results": results,
                "package_codes": package_codes
            }
            
        except Exception as e:
            logging.error(f"批量礼包打开异常: {e}")
            return {
                "success": False,
                "message": f"批量打开异常: {e}",
                "total_accounts": len(accounts) if accounts else 0,
                "total_packages": len(package_codes) if package_codes else 0,
                "total_operations": 0,
                "success_count": 0,
                "failure_count": 0,
                "results": [],
                "package_codes": package_codes if package_codes else []
            }
    
    def get_vip_voucher_count(self) -> Dict[str, Any]:
        """
        获取VIP礼券数量
        
        Returns:
            Dict[str, Any]: VIP礼券数量信息
        """
        try:
            logging.info("获取VIP礼券数量")
            
            response = self.post(
                action_path="g=Res&m=Depot&a=getDepotNum",
                data={
                    "key": self.key,
                    "code[]": "20102"  # VIP礼券代码
                }
            )
            
            success = response.get("status", False)
            message = response.get("msg", "")
            data = response.get("data", {})
            
            if success:
                num_arr = data.get("num_arr", {})
                voucher_count = int(num_arr.get("20102", "0"))
                
                logging.info(f"VIP礼券数量获取成功: {voucher_count} 张")
                return {
                    "success": True,
                    "message": message or "VIP礼券数量获取成功",
                    "voucher_count": voucher_count,
                    "raw_response": response
                }
            else:
                logging.warning(f"VIP礼券数量获取失败: {message}")
                return {
                    "success": False,
                    "message": message or "获取VIP礼券数量失败",
                    "voucher_count": 0,
                    "raw_response": response
                }
                
        except Exception as e:
            logging.error(f"获取VIP礼券数量异常: {e}")
            return {
                "success": False,
                "message": f"获取失败: {e}",
                "voucher_count": 0,
                "raw_response": {}
            }
    
    def vip_shop_purchase(self, goods_id: int, quantity: int = 1) -> Dict[str, Any]:
        """
        VIP商店购买商品
        
        Args:
            goods_id: 商品ID
            quantity: 购买数量，默认1
            
        Returns:
            Dict[str, Any]: 购买结果
        """
        try:
            logging.info(f"VIP商店购买: 商品ID {goods_id}, 数量 {quantity}")
            
            response = self.post(
                action_path="g=Res&m=Shop&a=buy",
                data={
                    "key": self.key,
                    "goods_id": str(goods_id),
                    "num": str(quantity)
                }
            )
            
            success = response.get("status", False)
            message = response.get("msg", "未知错误")
            purchase_data = response.get("data", {})
            
            if success:
                logging.info(f"VIP商店购买成功: {message}")
                return {
                    "success": True,
                    "message": message,
                    "purchase_info": purchase_data,
                    "goods_id": goods_id,
                    "quantity": quantity,
                    "raw_response": response
                }
            else:
                logging.warning(f"VIP商店购买失败: {message}")
                return {
                    "success": False,
                    "message": message,
                    "purchase_info": purchase_data,
                    "goods_id": goods_id,
                    "quantity": quantity,
                    "raw_response": response
                }
                
        except Exception as e:
            logging.error(f"VIP商店购买异常: {e}")
            return {
                "success": False,
                "message": f"购买失败: {e}",
                "purchase_info": {},
                "goods_id": goods_id,
                "quantity": quantity,
                "raw_response": {}
            }
    
    def batch_vip_shop_purchase(self, accounts: List[Dict[str, Any]], goods_id: int, quantity: int = 1) -> Dict[str, Any]:
        """
        批量VIP商店购买商品
        
        Args:
            accounts: 账户列表
            goods_id: 商品ID
            quantity: 购买数量，默认1
            
        Returns:
            Dict[str, Any]: 批量购买结果
        """
        try:
            logging.info(f"开始批量VIP商店购买: 商品ID {goods_id}, 数量 {quantity}, 涉及 {len(accounts)} 个账户")
            
            results = []
            success_count = 0
            failure_count = 0
            
            for i, account in enumerate(accounts, 1):
                username = account.get("username", f"账户{i}")
                key = account.get("key", "")
                cookie = account.get("cookie", {})
                
                logging.info(f"[{i}/{len(accounts)}] 为账户 {username} 购买VIP商品")
                
                # 创建临时VIP操作实例
                temp_vip_action = VipAction(key, cookie)
                result = temp_vip_action.vip_shop_purchase(goods_id, quantity)
                
                # 添加账户信息到结果
                result["account"] = {
                    "username": username,
                    "key": key,
                    "index": i
                }
                
                results.append(result)
                
                if result.get("success", False):
                    success_count += 1
                    logging.info(f"账户 {username} VIP商品购买成功")
                else:
                    failure_count += 1
                    logging.warning(f"账户 {username} VIP商品购买失败: {result.get('message', '未知错误')}")
            
            logging.info(f"批量VIP商店购买完成: 成功 {success_count} 个, 失败 {failure_count} 个")
            
            return {
                "success": True,
                "message": f"批量购买完成: 成功 {success_count}/{len(accounts)} 个账户",
                "total_accounts": len(accounts),
                "success_count": success_count,
                "failure_count": failure_count,
                "results": results,
                "goods_id": goods_id,
                "quantity": quantity
            }
            
        except Exception as e:
            logging.error(f"批量VIP商店购买异常: {e}")
            return {
                "success": False,
                "message": f"批量购买异常: {e}",
                "total_accounts": len(accounts) if accounts else 0,
                "success_count": 0,
                "failure_count": 0,
                "results": [],
                "goods_id": goods_id,
                "quantity": quantity
            }
    
    def get_gift_packages_in_depot(self, depot_action) -> Dict[str, Any]:
        """
        获取仓库中的礼包列表
        
        Args:
            depot_action: DepotAction实例
            
        Returns:
            Dict[str, Any]: 礼包列表信息
        """
        try:
            from src.delicious_town_bot.constants import ItemType
            
            # 获取所有道具
            props = depot_action.get_all_items(ItemType.PROPS)
            
            # 筛选礼包类物品
            gift_packages = []
            gift_package_keywords = [
                "礼包", "礼盒", "宝箱", "奖励包", "福袋", "红包", "礼券",
                "钻石礼包", "钻石", "愚人节", "节日礼包", "活动礼包",
                "新手礼包", "每日礼包", "签到礼包", "VIP礼包", "特惠礼包"
            ]
            
            for item in props:
                item_name = item.get("goods_name", item.get("name", ""))
                item_code = item.get("goods_code", item.get("code", ""))
                item_num_raw = item.get("num", 0)
                
                # 安全地转换数量为整数
                try:
                    item_num = int(item_num_raw) if item_num_raw is not None else 0
                except (ValueError, TypeError):
                    logging.warning(f"物品 {item_name} 的数量格式错误: {item_num_raw}，设为0")
                    item_num = 0
                
                # 检查是否是礼包类物品
                is_gift_package = False
                for keyword in gift_package_keywords:
                    if keyword in item_name:
                        is_gift_package = True
                        break
                
                if is_gift_package and item_num > 0:
                    gift_packages.append({
                        "name": item_name,
                        "code": item_code,
                        "num": item_num,
                        "raw_data": item
                    })
                    logging.debug(f"发现礼包: {item_name}, 数量: {item_num}, 代码: {item_code}")
            
            logging.info(f"仓库礼包统计: 共找到 {len(gift_packages)} 种礼包")
            return {
                "success": True,
                "message": f"成功获取 {len(gift_packages)} 种礼包",
                "gift_packages": gift_packages,
                "total_count": len(gift_packages)
            }
            
        except Exception as e:
            logging.error(f"获取仓库礼包列表异常: {e}")
            return {
                "success": False,
                "message": f"获取失败: {e}",
                "gift_packages": [],
                "total_count": 0
            }