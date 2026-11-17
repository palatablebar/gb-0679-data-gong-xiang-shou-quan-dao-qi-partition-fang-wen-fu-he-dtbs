# 接口

模块GET使用仓内样例，模块POST可传csv或rows与context，直接计算当前规则。/api/runs使用完整流水线并原子保存。每个阶段返回rows、quarantine、metrics；后续阶段还返回累计隔离。/api/upload接收multipart文件file。/api/runs/<id>/archive只导出一份带清单与证据的CSV。

对账阶段额外返回conflict_review：同一事件号的冲突原行逐条复核结论（越权放行证据/误拦截证据/执行一致）与取舍依据。证据导出中结论行kind=accepted（reason为通过/越权放行/误拦截，逐条不抵消），冲突原行kind=conflict（reason为复核结论，evidence含首条行号、差异字段与取舍依据），其余隔离行kind=quarantine。
