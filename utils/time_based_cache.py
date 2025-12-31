import time
from functools import wraps

def time_based_cache(expire_seconds=2):
    """
    装饰器：为每个参数组合（如不同股票代码）维护独立的时间缓存。
    如果距离上次调用该参数未超过 expire_seconds，则返回缓存值；
    否则重新执行函数并更新缓存。
    """
    def decorator(func):
        # 缓存结构：{ args_key: {'timestamp': ..., 'value': ...} }
        cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 构造可哈希的缓存键（要求参数必须可哈希）
            try:
                key = (args, tuple(sorted(kwargs.items())))
            except TypeError:
                raise TypeError("所有参数必须是可哈希类型（如 str, int 等），才能用于缓存键。")

            current_time = time.time()

            # 检查缓存是否存在且未过期
            if key in cache:
                cached_time, cached_value = cache[key]
                if current_time - cached_time < expire_seconds:
                    return cached_value  # 返回缓存值

            # 缓存过期或不存在，调用原函数
            result = func(*args, **kwargs)
            cache[key] = (current_time, result)
            return result

        # 可选：暴露缓存以便调试或清理
        wrapper._cache = cache
        return wrapper
    return decorator


# 模拟获取股票价格的函数（实际中可替换为真实API）
@time_based_cache(expire_seconds=2)
def get_stock_price(symbol: str) -> float:
    print(f"[API CALL] Fetching latest price for {symbol} at {time.strftime('%H:%M:%S')}")
    # 模拟价格：用时间戳生成伪随机但可读的价格
    pseudo_price = 100 + (hash(symbol) % 50) + (int(time.time() * 100) % 10)
    return round(pseudo_price, 2)


# 示例使用
if __name__ == "__main__":
    symbols = ["AAPL", "GOOGL", "TSLA"]

    # 第一次访问：全部触发 API 调用
    for sym in symbols:
        print(f"{sym}: {get_stock_price(sym)}")

    print("\n--- 等待1秒 ---\n")
    time.sleep(1)

    # 第二次访问（<2秒）：应全部命中缓存，无新 API 调用
    for sym in symbols:
        print(f"{sym}: {get_stock_price(sym)}")

    print("\n--- 等待1.5秒（总间隔 >2秒）---\n")
    time.sleep(1.5)

    # 第三次访问（>2秒）：应重新调用 API
    for sym in symbols:
        print(f"{sym}: {get_stock_price(sym)}")