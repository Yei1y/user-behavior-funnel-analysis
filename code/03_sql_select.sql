-- 新老用户占比
SELECT
	new_user,
	concat(round(count(*)/sum(count(*))over()*100,2),"%") AS '%'
FROM user_action
GROUP BY new_user;

-- 性别占比
SELECT
	sex,
	CONCAT(ROUND(COUNT(*)/sum(COUNT(*))OVER()*100,2),"%") AS '%'
FROM user_action
GROUP BY sex;

-- 年龄分布
SELECT
	CASE
		WHEN age <= 20 THEN '20岁及以下'
		WHEN age <= 30 THEN '21-30岁'
		WHEN age <= 40 THEN '31-40岁'
		ELSE '41岁及以上'
	END AS age_band,
	CONCAT(ROUND(COUNT(*)/sum(COUNT(*))OVER()*100,2),"%") AS '%'
FROM user_action
GROUP BY age_band;

-- 用户地区占比
SELECT
	market,
	CONCAT(ROUND(COUNT(*)/sum(COUNT(*))OVER()*100,2),"%") AS '%'
FROM user_action
GROUP BY market;

-- 线上访问设施（设备）占比
SELECT
	device,
	CONCAT(ROUND(COUNT(*)/sum(COUNT(*))OVER()*100,2),"%") AS '%'
FROM user_action
GROUP BY device;

-- 操作系统占比
SELECT
	operative_system,
	CONCAT(ROUND(COUNT(*)/sum(COUNT(*))OVER()*100,2),"%") AS '%'
FROM user_action
GROUP BY operative_system;

-- 用户活跃度分布
SELECT
	CASE
		WHEN total_pages_visited < 5 THEN '低活跃度'
		WHEN total_pages_visited < 10 THEN '中活跃度'
		ELSE '高活跃度'
	END AS activity_band,
	CONCAT(ROUND(COUNT(*)/sum(COUNT(*))OVER()*100,2),"%") AS '%'
FROM user_action
GROUP BY activity_band;

-- 用户转化情况
SELECT
	confirmation_page,
	CONCAT(ROUND(COUNT(*)/sum(COUNT(*))OVER()*100,2),"%") AS '%'
FROM user_action
GROUP BY confirmation_page;

-- 第一段：首页 → 列表页
SELECT
	CONCAT(ROUND(SUM(listing_page)/SUM(home_page)*100,2),"%") AS '首页到列表页转化率',
	SUM(listing_page) AS '到达列表页会话数',
	SUM(home_page) AS '到达首页会话数'
FROM user_action;

-- 第二段：列表页 → 商品详情页
SELECT
	CONCAT(ROUND(SUM(product_page)/SUM(listing_page)*100,2),"%") AS '列表页到详情页转化率',
	SUM(product_page) AS '到达详情页会话数',
	SUM(listing_page) AS '到达列表页会话数'
FROM user_action;

-- 第三段：商品详情页 → 支付页
SELECT
	CONCAT(ROUND(SUM(payment_page)/SUM(product_page)*100,2),"%") AS '详情页到支付页转化率',
	SUM(payment_page) AS '到达支付页会话数',
	SUM(product_page) AS '到达详情页会话数'
FROM user_action;

-- 第四段：支付页 → 确认页
SELECT
	CONCAT(ROUND(SUM(confirmation_page)/SUM(payment_page)*100,2),"%") AS '支付页到确认页转化率',
	SUM(confirmation_page) AS '到达确认页会话数',
	SUM(payment_page) AS '到达支付页会话数'
FROM user_action;

-- 整体转化率：首页 → 确认页
SELECT
	CONCAT(ROUND(SUM(confirmation_page)/SUM(home_page)*100,2),"%") AS '整体转化率'
FROM user_action;

-- 新老用户维度的平均转化率
SELECT
	new_user,
	CONCAT(ROUND(SUM(confirmation_page)/COUNT(*)*100,2),"%") AS '平均转化率'
FROM user_action
GROUP BY new_user;

-- 性别维度的平均转化率
SELECT
	sex,
	CONCAT(ROUND(SUM(confirmation_page)/COUNT(*)*100,2),"%") AS '平均转化率'
FROM user_action
GROUP BY sex;

-- 年龄段维度的平均转化率
SELECT
	CASE
		WHEN age <= 20 THEN '20岁及以下'
		WHEN age <= 30 THEN '21-30岁'
		WHEN age <= 40 THEN '31-40岁'
		ELSE '41岁及以上'
	END AS age_band,
	CONCAT(ROUND(SUM(confirmation_page)/COUNT(*)*100,2),"%") AS '平均转化率'
FROM user_action
GROUP BY age_band;

-- 地区维度的平均转化率
SELECT
	market,
	CONCAT(ROUND(SUM(confirmation_page)/COUNT(*)*100,2),"%") AS '平均转化率'
FROM user_action
GROUP BY market;

-- 设备维度的平均转化率
SELECT
	device,
	CONCAT(ROUND(SUM(confirmation_page)/COUNT(*)*100,2),"%") AS '平均转化率'
FROM user_action
GROUP BY device;

-- 操作系统维度的平均转化率
SELECT
	operative_system,
	CONCAT(ROUND(SUM(confirmation_page)/COUNT(*)*100,2),"%") AS '平均转化率'
FROM user_action
GROUP BY operative_system;

-- 来源维度的平均转化率
SELECT
	source,
	CONCAT(ROUND(SUM(confirmation_page)/COUNT(*)*100,2),"%") AS '平均转化率'
FROM user_action
GROUP BY source;

-- 活跃度维度的平均转化率
SELECT
	CASE
		WHEN total_pages_visited < 5 THEN '低活跃度'
		WHEN total_pages_visited < 10 THEN '中活跃度'
		ELSE '高活跃度'
	END AS activity_band,
	CONCAT(ROUND(SUM(confirmation_page)/COUNT(*)*100,2),"%") AS '平均转化率'
FROM user_action
GROUP BY activity_band;