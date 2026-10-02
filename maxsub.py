
def max_sum(nums):
    best = nums[0]
    for i in range(len(nums)):        # i = 段的起点
        s = 0
        for j in range(i, len(nums)): # j = 段的终点（从起点一路向右延伸）
            s += nums[j]              # 延伸一步，就累加一步——不用重算整段
            best = max(best, s)       # 每个出现的段都和冠军比一比
    return best

def max_profit(prices):
    best = 0
    for i in range (len(prices)):
        for j in range(i+1 , len(prices)):
            profit = prices[j] - prices[i]
            best = max(best, profit)
    return best

print(max_profit([7, 1, 5, 3, 6, 4]))  # 应得 5
print(max_profit([2,8,3]))  # 应得 0