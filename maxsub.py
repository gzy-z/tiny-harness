
def max_sum(nums):
    best = nums[0]
    for i in range(len(nums)):        # i = 段的起点
        s = 0
        for j in range(i, len(nums)): # j = 段的终点（从起点一路向右延伸）
            s += nums[j]              # 延伸一步，就累加一步——不用重算整段
            best = max(best, s)       # 每个出现的段都和冠军比一比
    return best

print(max_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]))  # 应该打印 6
def max_sum(nums):
    best = nums[0]
    count = 0                      # 计数器
    for i in range(len(nums)):
        s = 0
        for j in range(i, len(nums)):
            s += nums[j]
            count += 1             # 最里面这行，跑一次数一次
            best = max(best, s)
    print(f"n={len(nums)}, 最内层跑了 {count} 次")
    return best

max_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4])   # n = 9
max_sum([1]*18)                             # n = 18（翻倍了）