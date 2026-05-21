# 苍穹外卖 day10 复习笔记：定时任务与 WebSocket 实时提醒

day10 的主题是 **订单状态自动处理** 和 **实时消息提醒**。核心内容包括：

1. Spring Task 定时任务
2. 订单状态定时处理
3. WebSocket 长连接
4. 来单提醒
5. 客户催单

这一天不要只记注解和接口路径，要能说清楚：**哪些业务不适合等用户主动操作，哪些消息必须由服务端主动推给管理端页面**。

---

## 1. 当天课程主线

### 1.1 Spring Task 解决什么问题

Spring Task 是 Spring 提供的任务调度工具，用来按照约定时间自动执行 Java 代码。

典型场景：

```text
支付超时订单自动取消
派送中订单定时改为已完成
固定时间发送提醒或通知
```

使用步骤：

```text
引入 spring-context 相关依赖
        ↓
启动类添加 @EnableScheduling
        ↓
自定义任务类交给 Spring 管理
        ↓
方法上添加 @Scheduled(cron = "...")
```

当前项目中，启动类 `SkyApplication` 已有 `@EnableCaching` 和事务注解，但 day10 讲义要求还要补上：

```java
@EnableScheduling
```

否则定时任务类即使写了 `@Scheduled`，也不会被调度执行。

### 1.2 cron 表达式

cron 表达式用来定义任务触发时间。Spring Task 常见写法是 6 个域：

```text
秒 分 时 日 月 周
```

常见例子：

```text
0/5 * * * * ?     每 5 秒执行一次
0 * * * * ?       每分钟整点执行一次
0 0 1 * * ?       每天凌晨 1 点执行一次
```

易错点是 **日** 和 **周** 通常不要同时指定，其中一个用 `?` 表示不关心。

---

## 2. 订单状态定时处理

### 2.1 需求背景

订单可能长时间停在异常状态：

```text
用户下单后未支付，订单一直是待支付
用户已经收货，但管理端没有点完成，订单一直是派送中
```

所以需要定时任务兜底：

```text
每分钟检查一次：
待支付并且下单超过 15 分钟的订单，改为已取消

每天凌晨 1 点检查一次：
派送中并且下单超过 1 小时的订单，改为已完成
```

### 2.2 类和方法关系

```text
OrderTask
        ↓
OrderMapper.getByStatusAndOrdertimeLT(status, orderTime)
        ↓
查询 orders 表中满足状态和时间条件的订单
        ↓
逐条构造 Orders 更新对象
        ↓
OrderMapper.update(orders)
```

需要新增或补充的关键点：

```text
sky-server/src/main/java/com/sky/task/OrderTask.java
sky-server/src/main/java/com/sky/mapper/OrderMapper.java
sky-server/src/main/java/com/sky/SkyApplication.java
```

### 2.3 支付超时订单逻辑

核心判断条件：

```text
status = Orders.PENDING_PAYMENT
order_time < 当前时间 - 15 分钟
```

核心代码骨架：

```java
@Scheduled(cron = "0 * * * * ?")
public void processTimeoutOrder() {
    LocalDateTime time = LocalDateTime.now().plusMinutes(-15);
    List<Orders> ordersList =
            orderMapper.getByStatusAndOrdertimeLT(Orders.PENDING_PAYMENT, time);

    if (ordersList != null && !ordersList.isEmpty()) {
        ordersList.forEach(order -> {
            order.setStatus(Orders.CANCELLED);
            order.setCancelReason("支付超时，自动取消");
            order.setCancelTime(LocalDateTime.now());
            orderMapper.update(order);
        });
    }
}
```

这里不是删除订单，而是改订单状态。这样可以保留业务记录，后续也能查到订单为什么取消。

### 2.4 派送中订单逻辑

核心判断条件：

```text
status = Orders.DELIVERY_IN_PROGRESS
order_time < 当前时间 - 1 小时
```

核心代码骨架：

```java
@Scheduled(cron = "0 0 1 * * ?")
public void processDeliveryOrder() {
    LocalDateTime time = LocalDateTime.now().plusMinutes(-60);
    List<Orders> ordersList =
            orderMapper.getByStatusAndOrdertimeLT(Orders.DELIVERY_IN_PROGRESS, time);

    if (ordersList != null && !ordersList.isEmpty()) {
        ordersList.forEach(order -> {
            order.setStatus(Orders.COMPLETED);
            orderMapper.update(order);
        });
    }
}
```

讲义里用 `order_time` 做时间条件。复习时要能说明：它的作用是筛掉刚进入派送中的订单，避免刚派送就被自动完成。

### 2.5 Mapper 查询

讲义要求在 `OrderMapper` 增加：

```java
@Select("select * from orders where status = #{status} and order_time < #{orderTime}")
List<Orders> getByStatusAndOrdertimeLT(Integer status, LocalDateTime orderTime);
```

当前源码里的 `OrderMapper` 还只有：

```text
insert
getByNumber
update
```

所以学习 day10 时，需要明确这是一个新增能力，不是现有代码里已经完成的部分。

---

## 3. WebSocket

### 3.1 WebSocket 和 HTTP 的区别

HTTP：

```text
短连接
客户端请求，服务端响应
服务端不能主动把消息推给浏览器
```

WebSocket：

```text
长连接
一次握手后保持连接
浏览器和服务端可以双向通信
服务端可以主动推送消息
```

day10 使用 WebSocket 的原因是：管理端需要第一时间知道新订单或催单，不能等页面轮询接口。

### 3.2 WebSocket 入门案例结构

讲义里的入门案例有 5 个部分：

```text
websocket.html                  浏览器客户端
spring-boot-starter-websocket   Maven 依赖
WebSocketServer                 服务端连接和消息处理
WebSocketConfiguration          注册 ServerEndpointExporter
WebSocketTask                   定时向浏览器推送消息
```

服务端地址：

```java
@ServerEndpoint("/ws/{sid}")
```

浏览器连接：

```javascript
websocket = new WebSocket("ws://localhost:8080/ws/" + clientId);
```

### 3.3 WebSocketServer 的职责

```text
onOpen      连接建立，保存 session
onMessage   收到浏览器消息
onClose     连接关闭，移除 session
sendToAllClient 群发消息给所有已连接客户端
```

核心数据结构：

```java
private static Map<String, Session> sessionMap = new HashMap<>();
```

`sid` 是连接标识，`Session` 是当前浏览器和服务端之间的连接对象。

发送消息的核心代码：

```java
session.getBasicRemote().sendText(message);
```

这个方法是真正把服务端消息推到浏览器的地方。

### 3.4 配置类的作用

`WebSocketConfiguration` 中注册：

```java
@Bean
public ServerEndpointExporter serverEndpointExporter() {
    return new ServerEndpointExporter();
}
```

它的作用是让 Spring 能扫描并注册 `@ServerEndpoint` 标注的 WebSocket 服务端点。没有这个配置，`/ws/{sid}` 端点不会正常生效。

---

## 4. 来单提醒

### 4.1 业务目标

用户下单并支付成功后，管理端需要马上收到提醒：

```text
弹窗提示
语音播报
```

设计思路：

```text
管理端浏览器登录后建立 WebSocket 长连接
        ↓
用户在小程序支付成功
        ↓
后端 paySuccess 修改订单状态
        ↓
后端通过 WebSocket 推送 JSON 消息
        ↓
管理端根据 type 判断是来单提醒并播放提示
```

### 4.2 消息格式

服务端推送给管理端的 JSON 约定：

```json
{
  "type": 1,
  "orderId": 订单id,
  "content": "订单号：xxx"
}
```

字段含义：

```text
type = 1      来单提醒
orderId       订单 id
content       页面展示和语音播报内容
```

### 4.3 paySuccess 中需要补的逻辑

当前源码里的 `paySuccess` 已经完成了支付成功后的订单状态修改：

```text
待支付 -> 待接单
未支付 -> 已支付
记录 checkoutTime
```

day10 要在这个方法后面补 WebSocket 推送：

```java
Map map = new HashMap();
map.put("type", 1);
map.put("orderId", orders.getId());
map.put("content", "订单号：" + outTradeNo);

webSocketServer.sendToAllClient(JSON.toJSONString(map));
```

易错点：`OrderServiceImpl` 要注入 `WebSocketServer`，并确保 WebSocket 相关配置类已经生效。

---

## 5. 客户催单

### 5.1 业务目标

用户在小程序点击催单后，商家端要立刻收到提醒。

设计思路：

```text
小程序点击催单
        ↓
请求 /user/order/reminder/{id}
        ↓
Controller 调用 orderService.reminder(id)
        ↓
Service 查询订单是否存在
        ↓
通过 WebSocket 推送催单消息
        ↓
管理端弹窗和语音播报
```

### 5.2 接口和代码关系

Controller：

```java
@GetMapping("/reminder/{id}")
@ApiOperation("用户催单")
public Result reminder(@PathVariable("id") Long id) {
    orderService.reminder(id);
    return Result.success();
}
```

Service 接口：

```java
void reminder(Long id);
```

Service 实现：

```java
public void reminder(Long id) {
    Orders orders = orderMapper.getById(id);
    if (orders == null) {
        throw new OrderBusinessException(MessageConstant.ORDER_NOT_FOUND);
    }

    Map map = new HashMap();
    map.put("type", 2);
    map.put("orderId", id);
    map.put("content", "订单号：" + orders.getNumber());
    webSocketServer.sendToAllClient(JSON.toJSONString(map));
}
```

Mapper：

```java
@Select("select * from orders where id=#{id}")
Orders getById(Long id);
```

### 5.3 催单消息格式

```json
{
  "type": 2,
  "orderId": 订单id,
  "content": "订单号：xxx"
}
```

`type = 2` 表示客户催单。管理端页面通过 `type` 区分播放哪种提醒音频、显示哪种提示内容。

---

## 6. 当前源码对照

当前工程源码已经有 day08 订单提交和支付相关基础，但 day10 相关代码还没补齐：

```text
SkyApplication.java
    已有 @EnableCaching
    还缺 @EnableScheduling

OrderMapper.java
    已有 insert / getByNumber / update
    还缺 getByStatusAndOrdertimeLT / getById

OrderServiceImpl.java
    已有 submitOrder / payment / paySuccess
    paySuccess 还缺来单提醒 WebSocket 推送
    还缺 reminder(id) 催单逻辑

OrderController.java
    已有 /submit 和 /payment
    还缺 /reminder/{id}

sky-server/src/main/java/com/sky/task
    当前未看到 OrderTask / WebSocketTask

sky-server/src/main/java/com/sky/websocket
    当前未看到 WebSocketServer

sky-server/src/main/java/com/sky/config
    当前未看到 WebSocketConfiguration
```

所以这份笔记是 day10 的实现蓝图：先理解讲义流程，再按这些类和方法补到当前工程。

---

## 7. 易错点和排错

### 7.1 定时任务不执行

优先检查：

```text
启动类是否添加 @EnableScheduling
任务类是否有 @Component
任务方法是否是 public void
cron 表达式是否正确
服务是否正常启动
```

测试时可以临时把 cron 改成高频，比如每 5 秒执行一次，确认日志和数据库变化。

### 7.2 订单没有被自动取消

优先检查：

```text
订单 status 是否等于 Orders.PENDING_PAYMENT
order_time 是否早于当前时间 15 分钟
Mapper 查询条件是否写成 order_time < #{orderTime}
OrderMapper.update 是否能只更新非空字段
```

### 7.3 WebSocket 连接不上

优先检查：

```text
是否引入 spring-boot-starter-websocket
是否注册 ServerEndpointExporter
@ServerEndpoint 路径是否和前端 ws:// 地址一致
后端服务端口是否是 8080
浏览器控制台是否有连接错误
```

### 7.4 管理端收不到来单提醒

优先检查：

```text
管理端页面是否已经建立 WebSocket 长连接
paySuccess 是否真的被调用
WebSocketServer 是否注入成功
sendToAllClient 是否拿到了 session
推送 JSON 中 type 是否为 1
```

### 7.5 客户催单失败

优先检查：

```text
接口路径是否是 GET /user/order/reminder/{id}
订单 id 是否存在
OrderMapper.getById 是否正确
推送 JSON 中 type 是否为 2
```

---

## 8. 复习检查清单

你能回答这些问题，day10 基本就掌握了：

```text
[ ] Spring Task 的作用是什么？
[ ] @EnableScheduling 加在哪里？不加会怎样？
[ ] @Scheduled(cron = "0 * * * * ?") 表示什么？
[ ] 支付超时订单为什么要改为已取消，而不是删除？
[ ] 派送中订单为什么要做定时兜底？
[ ] WebSocket 和 HTTP 的区别是什么？
[ ] @ServerEndpoint("/ws/{sid}") 中 sid 有什么用？
[ ] ServerEndpointExporter 的作用是什么？
[ ] sendToAllClient 为什么能实现群发？
[ ] 来单提醒的 type 是多少？
[ ] 客户催单的 type 是多少？
[ ] /user/order/reminder/{id} 的 Controller、Service、Mapper 调用链是什么？
[ ] 当前工程要补 day10 功能，需要改哪些类？
```

