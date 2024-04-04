class Solution(object):
    def maxDepth(self, s):
        depth = 0
        opened = 0

        for char in list(s):
            if char == "(":
                opened += 1

            if char == ")":
                if opened > depth:
                    depth = opened
                opened -= 1

        return depth


print(Solution().maxDepth("(1)+((2))+(((3)))"))
