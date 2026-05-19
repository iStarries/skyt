# 苍穹外卖 day08 复习笔记：地址簿、用户下单与微信支付

day08 的主线是把 C 端从“能选商品”推进到“能提交订单并进入支付流程”。本次代码已经完成地址簿模块导入、用户下单、微信支付代码导入；微信支付准备工作中的真实商户证书、私钥和 cpolar 公网回调地址还没有配置，因此支付接口目前适合编译和流程学习，不适合真实调起微信支付。

---

## 1. 当天课程主线

1. 用户地址簿
2. 用户下单
3. 微信支付准备工作
4. 微信支付代码导入

对应的数据流是：

```text
地址簿 address_book
        -> 购物车 shopping_cart
        -> 订单 orders
        -> 订单明细 order_detail
        -> 微信支付预支付交易单
        -> 支付成功回调更新订单状态
```

---

## 2. 地址簿模块

地址簿是 C 端下单前的基础数据。用户下单时必须选择一个收货地址，后端通过 `addressBookId` 查询 `address_book`，再把收货人、手机号、详细地址复制到订单表。

关键接口：

| 功能 | 方法 | 路径 |
| --- | --- | --- |
| 查询当前用户地址 | GET | `/user/addressBook/list` |
| 新增地址 | POST | `/user/addressBook` |
| 根据 id 查询 | GET | `/user/addressBook/{id}` |
| 修改地址 | PUT | `/user/addressBook` |
| 设置默认地址 | PUT | `/user/addressBook/default` |
| 删除地址 | DELETE | `/user/addressBook?id=xx` |
| 查询默认地址 | GET | `/user/addressBook/default` |

核心关系：

```text
AddressBookController
        -> AddressBookService
        -> AddressBookServiceImpl
        -> AddressBookMapper
        -> AddressBookMapper.xml
        -> address_book
```

设置默认地址要分两步，并且需要事务：

```text
1. 当前用户所有地址 is_default = 0
2. 当前选中的地址 is_default = 1
```

---

## 3. 用户下单

下单接口：

```text
POST /user/order/submit
```

请求 DTO：

```java
public class OrdersSubmitDTO {
    private Long addressBookId;
    private int payMethod;
    private String remark;
    private LocalDateTime estimatedDeliveryTime;
    private Integer deliveryStatus;
    private Integer tablewareNumber;
    private Integer tablewareStatus;
    private Integer packAmount;
    private BigDecimal amount;
}
```

返回 VO：

```java
public class OrderSubmitVO {
    private Long id;
    private String orderNumber;
    private BigDecimal orderAmount;
    private LocalDateTime orderTime;
}
```

下单业务流程：

```text
OrderController.submit
        -> OrderService.submitOrder
        -> 根据 addressBookId 查询地址
        -> 查询当前用户购物车
        -> 构造 Orders
        -> insert orders，回填订单 id
        -> 购物车数据复制成 OrderDetail 列表
        -> 批量 insert order_detail
        -> 删除当前用户购物车
        -> 返回 OrderSubmitVO
```

重要校验：

```java
if (addressBook == null) {
    throw new AddressBookBusinessException(MessageConstant.ADDRESS_BOOK_IS_NULL);
}

if (shoppingCartList == null || shoppingCartList.isEmpty()) {
    throw new ShoppingCartBusinessException(MessageConstant.SHOPPING_CART_IS_NULL);
}
```

订单初始状态：

```java
order.setStatus(Orders.PENDING_PAYMENT);
order.setPayStatus(Orders.UN_PAID);
order.setOrderTime(LocalDateTime.now());
```

---

## 4. 订单表与订单明细表

用户提交一次订单时，至少要写两张表：

```text
orders：一条订单主记录
order_detail：一条或多条订单明细记录
```

`orders.id` 是主键，插入订单后通过 MyBatis 的 `useGeneratedKeys` 回填：

```xml
<insert id="insert" parameterType="Orders" useGeneratedKeys="true" keyProperty="id">
```

然后订单明细使用这个订单 id：

```java
orderDetail.setOrderId(order.getId());
```

批量插入订单明细：

```xml
<foreach collection="orderDetails" item="od" separator=",">
    (#{od.name}, #{od.orderId}, #{od.dishId}, #{od.setmealId}, #{od.dishFlavor},
     #{od.number}, #{od.amount}, #{od.image})
</foreach>
```

---

## 5. 微信支付准备工作

3.2 节不是单纯写代码，而是准备真实支付运行环境：

1. 商户号 `mchid`
2. 商户 API 证书序列号 `mchSerialNo`
3. 商户私钥文件 `apiclient_key.pem`
4. 微信支付平台证书
5. APIv3 密钥
6. 支付成功回调地址 `notifyUrl`
7. 退款成功回调地址 `refundNotifyUrl`
8. cpolar 之类的内网穿透公网地址

当前项目已经把配置项补齐，但 `application-dev.yml` 中这些值暂时为空：

```yaml
sky:
  wechat:
    mchid: ''
    mchSerialNo: ''
    privateKeyFilePath: ''
    apiV3Key: ''
    weChatPayCertFilePath: ''
    notifyUrl: ''
    refundNotifyUrl: ''
```

这样做的结果是：

- 编译和普通启动不受影响。
- 下单接口 `/user/order/submit` 可以继续学习和测试。
- 真正调用 `/user/order/payment` 时，会因为商户证书或密钥缺失而失败。

---

## 6. 微信支付代码流程

支付接口：

```text
PUT /user/order/payment
```

流程：

```text
OrderController.payment
        -> OrderService.payment
        -> UserMapper.getById 查询当前用户 openid
        -> WeChatPayUtil.pay 调用微信 JSAPI 下单
        -> 返回 OrderPaymentVO 给小程序调起支付
```

支付成功后，微信会请求回调接口：

```text
/notify/paySuccess
```

回调处理流程：

```text
PayNotifyController.paySuccessNotify
        -> 读取微信回调 body
        -> 使用 apiV3Key 解密 resource
        -> 取出 out_trade_no
        -> OrderService.paySuccess(outTradeNo)
        -> 根据订单号查询订单
        -> 更新订单状态为待接单、支付状态为已支付、设置结账时间
        -> 响应微信 SUCCESS
```

订单支付成功后的状态更新：

```java
Orders orders = Orders.builder()
        .id(ordersDB.getId())
        .status(Orders.TO_BE_CONFIRMED)
        .payStatus(Orders.PAID)
        .checkoutTime(LocalDateTime.now())
        .build();

orderMapper.update(orders);
```

---

## 7. 当前代码文件关系

地址簿：

```text
AddressBookController
AddressBookService
AddressBookServiceImpl
AddressBookMapper
AddressBookMapper.xml
```

下单与支付：

```text
OrderController
OrderService
OrderServiceImpl
OrderMapper
OrderMapper.xml
OrderDetailMapper
OrderDetailMapper.xml
PayNotifyController
```

配置与工具：

```text
WeChatProperties
WeChatPayUtil
application.yml
application-dev.yml
```

DTO / Entity / VO：

```text
OrdersSubmitDTO
OrdersPaymentDTO
Orders
OrderDetail
OrderSubmitVO
OrderPaymentVO
AddressBook
ShoppingCart
```

---

## 8. 易错点和排错

### 8.1 下单后必须清空当前用户购物车

清空购物车必须按当前用户 id 删除：

```java
shoppingCartMapper.deleteByUserId(userId);
```

不要写成删除整张 `shopping_cart` 表，否则会影响其他用户。

### 8.2 订单明细必须在订单插入之后写

`order_detail.order_id` 依赖 `orders.id`。如果订单主表还没插入，明细表拿不到订单 id。

### 8.3 `OrderMapper.insert` 要回填主键

如果 XML 忘了：

```xml
useGeneratedKeys="true" keyProperty="id"
```

后面 `order.getId()` 可能为空，导致订单明细关联失败。

### 8.4 3.2 没做时不要真实测支付

没有商户私钥、平台证书、APIv3Key 时，`WeChatPayUtil.getClient()` 无法正常构造微信支付 HTTP 客户端。

### 8.5 回调地址必须是公网可访问

微信支付成功回调是微信服务器主动请求你的后端接口。本地 `localhost:8080` 对微信不可见，需要 cpolar 或其他内网穿透地址。

### 8.6 `apiV3Key` 为空会导致回调解密失败

`PayNotifyController.decryptData()` 使用：

```java
new AesUtil(weChatProperties.getApiV3Key().getBytes(StandardCharsets.UTF_8))
```

如果 `apiV3Key` 为空，支付成功回调无法正常解密。

---

## 9. 接口速查

| 功能 | 方法 | 路径 |
| --- | --- | --- |
| 查询地址簿 | GET | `/user/addressBook/list` |
| 新增地址 | POST | `/user/addressBook` |
| 设置默认地址 | PUT | `/user/addressBook/default` |
| 查询默认地址 | GET | `/user/addressBook/default` |
| 提交订单 | POST | `/user/order/submit` |
| 订单支付 | PUT | `/user/order/payment` |
| 支付成功回调 | ANY | `/notify/paySuccess` |

---

## 10. 自测清单

1. 能否说清楚 `address_book`、`shopping_cart`、`orders`、`order_detail` 四张表的关系？
2. 为什么下单前要校验地址簿是否为空？
3. 为什么购物车为空不能下单？
4. 为什么订单主表插入后才能插入订单明细？
5. `useGeneratedKeys` 和 `keyProperty="id"` 的作用是什么？
6. 下单为什么要加 `@Transactional`？
7. 支付成功后订单状态应该从什么变成什么？
8. `PayNotifyController` 为什么需要解密微信回调数据？
9. 3.2 没做时，为什么编译可以通过但真实支付会失败？
10. cpolar 临时域名在微信支付回调中解决了什么问题？
