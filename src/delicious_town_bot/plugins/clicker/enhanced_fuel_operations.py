#!/usr/bin/env python3
"""
增强版加油操作模块
集成真实API，优化错误处理和日志记录
"""
import time
from typing import Tuple, Dict, Any, Optional
from datetime import datetime

from src.delicious_town_bot.actions.restaurant import RestaurantActions
from src.delicious_town_bot.actions.base_action import BusinessLogicError


class EnhancedFuelOperations:
    """增强版加油操作类"""
    
    def __init__(self, enable_detailed_logging: bool = True):
        self.enable_detailed_logging = enable_detailed_logging
        self.operation_stats = {
            "total_attempts": 0,
            "successful_fuel_ups": 0,
            "already_full_count": 0,
            "failed_operations": 0,
            "api_errors": 0
        }
    
    def execute_fuel_up(self, key: str, username: str = "未知账号") -> Tuple[bool, str]:
        """
        执行增强版加油操作
        
        Args:
            key: 账号的API密钥
            username: 账号用户名（用于日志记录）
            
        Returns:
            Tuple[bool, str]: (是否成功, 详细消息)
        """
        self.operation_stats["total_attempts"] += 1
        
        if self.enable_detailed_logging:
            print(f"🔧 [{datetime.now().strftime('%H:%M:%S')}] 开始为账号 '{username}' 执行加油操作...")
        
        try:
            # 创建餐厅操作实例
            restaurant_action = RestaurantActions(key=key, cookie={"PHPSESSID": "dummy"})
            
            # 步骤1: 获取当前餐厅状态
            status_result = self._get_restaurant_status(restaurant_action, username)
            if not status_result["success"]:
                self.operation_stats["api_errors"] += 1
                return False, status_result["message"]
            
            status = status_result["data"]
            oil_current = status.get("oil_current", 0)
            oil_max = status.get("oil_max", 0)
            
            # 步骤2: 检查是否需要加油
            if oil_current >= oil_max:
                self.operation_stats["already_full_count"] += 1
                success_msg = f"油量已满 ({oil_current}/{oil_max})，无需加油"
                if self.enable_detailed_logging:
                    print(f"   ✅ {success_msg}")
                return True, success_msg
            
            # 步骤3: 执行加油操作
            fuel_result = self._execute_refill(restaurant_action, username, oil_current, oil_max)
            if fuel_result["success"]:
                self.operation_stats["successful_fuel_ups"] += 1
                return True, fuel_result["message"]
            else:
                self.operation_stats["failed_operations"] += 1
                return False, fuel_result["message"]
                
        except BusinessLogicError as e:
            # 游戏业务逻辑错误
            self.operation_stats["api_errors"] += 1
            error_msg = f"游戏API错误: {str(e)}"
            if self.enable_detailed_logging:
                print(f"   ❌ {error_msg}")
            return False, error_msg
            
        except Exception as e:
            # 其他异常
            self.operation_stats["failed_operations"] += 1
            error_msg = f"操作异常: {str(e)}"
            if self.enable_detailed_logging:
                print(f"   ❌ {error_msg}")
            return False, error_msg
    
    def _get_restaurant_status(self, restaurant_action: RestaurantActions, username: str) -> Dict[str, Any]:
        """获取餐厅状态的内部方法"""
        try:
            if self.enable_detailed_logging:
                print(f"   📊 正在获取 '{username}' 的餐厅状态...")
            
            status = restaurant_action.get_status()
            
            if status is None:
                return {
                    "success": False,
                    "message": "无法获取餐厅状态，可能是网络问题或Key已失效"
                }
            
            if self.enable_detailed_logging:
                oil_info = f"{status.get('oil_current', 0)}/{status.get('oil_max', 0)}"
                special_dishes = status.get('special_dish_remaining', 0)
                print(f"   📊 状态获取成功: 油量 {oil_info}, 特色菜剩余 {special_dishes}")
            
            return {
                "success": True,
                "data": status,
                "message": "状态获取成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"获取状态失败: {str(e)}"
            }
    
    def _execute_refill(self, restaurant_action: RestaurantActions, username: str, 
                       current_oil: int, max_oil: int) -> Dict[str, Any]:
        """执行加油的内部方法"""
        try:
            if self.enable_detailed_logging:
                print(f"   ⛽ 正在为 '{username}' 加油 (当前 {current_oil}/{max_oil})...")
            
            success, message = restaurant_action.refill_oil()
            
            if success:
                # 清理HTML标签和格式化消息
                clean_message = message.replace("<br>", " / ").strip()
                result_msg = f"加油成功: {clean_message}"
                
                if self.enable_detailed_logging:
                    print(f"   ✅ {result_msg}")
                
                return {
                    "success": True,
                    "message": result_msg
                }
            else:
                error_msg = f"加油失败: {message}"
                
                if self.enable_detailed_logging:
                    print(f"   ❌ {error_msg}")
                
                return {
                    "success": False,
                    "message": error_msg
                }
                
        except Exception as e:
            error_msg = f"加油执行异常: {str(e)}"
            if self.enable_detailed_logging:
                print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """获取操作统计信息"""
        stats = self.operation_stats.copy()
        
        # 计算成功率
        if stats["total_attempts"] > 0:
            stats["success_rate"] = round(
                (stats["successful_fuel_ups"] + stats["already_full_count"]) / stats["total_attempts"] * 100, 2
            )
        else:
            stats["success_rate"] = 0.0
        
        # 添加时间戳
        stats["last_updated"] = datetime.now().isoformat()
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.operation_stats = {
            "total_attempts": 0,
            "successful_fuel_ups": 0,
            "already_full_count": 0,
            "failed_operations": 0,
            "api_errors": 0
        }
    
    def print_summary(self):
        """打印操作摘要"""
        stats = self.get_operation_stats()
        
        print("\n" + "="*50)
        print("🔧 加油操作统计摘要")
        print("="*50)
        print(f"📊 总尝试次数: {stats['total_attempts']}")
        print(f"✅ 成功加油: {stats['successful_fuel_ups']}")
        print(f"🔋 油量已满跳过: {stats['already_full_count']}")
        print(f"❌ 操作失败: {stats['failed_operations']}")
        print(f"🚨 API错误: {stats['api_errors']}")
        print(f"📈 成功率: {stats['success_rate']}%")
        print("="*50)


def create_enhanced_fuel_worker():
    """创建增强版加油工作器的工厂函数"""
    fuel_ops = EnhancedFuelOperations(enable_detailed_logging=True)
    
    def enhanced_fuel_up(key: str, username: str = "未知账号") -> Tuple[bool, str]:
        """增强版加油操作函数"""
        return fuel_ops.execute_fuel_up(key, username)
    
    # 将统计方法绑定到函数上
    enhanced_fuel_up.get_stats = fuel_ops.get_operation_stats
    enhanced_fuel_up.print_summary = fuel_ops.print_summary
    enhanced_fuel_up.reset_stats = fuel_ops.reset_stats
    
    return enhanced_fuel_up


# 使用示例和测试
if __name__ == "__main__":
    print("🚀 增强版加油操作模块测试...")
    
    # 创建增强版加油操作实例
    fuel_ops = EnhancedFuelOperations(enable_detailed_logging=True)
    
    # 模拟测试
    print("\n📝 模拟测试场景:")
    
    # 场景1: 模拟无效Key
    print("\n1. 测试无效Key场景:")
    success, message = fuel_ops.execute_fuel_up("invalid_key", "测试账号1")
    print(f"   结果: {'成功' if success else '失败'} - {message}")
    
    # 场景2: 模拟正常账号（但实际不调用API）
    print("\n2. 测试结果展示:")
    fuel_ops.operation_stats["total_attempts"] = 10
    fuel_ops.operation_stats["successful_fuel_ups"] = 7
    fuel_ops.operation_stats["already_full_count"] = 2
    fuel_ops.operation_stats["failed_operations"] = 1
    
    # 打印统计摘要
    fuel_ops.print_summary()
    
    print("\n✅ 增强版加油操作模块测试完成")