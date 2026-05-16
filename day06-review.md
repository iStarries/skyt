# 苍穹外卖 day06 复习笔记：微信登录与商品浏览

day06 的主线是从用户端小程序进入后端：先学会 Java 后端如何主动发送 HTTP 请求，再用这个能力完成微信登录，最后导入用户端商品浏览接口。复习时不要只记接口路径，要能说清楚 `code -> openid -> user -> token -> 后续请求携带 token` 这一整条链路。

---

## 1. 当天课程主线

day06 包含四块内容：

1. `HttpClient`：Java 程序主动访问其他 HTTP 服务。
2. 微信小程序开发入门：小程序目录、编译、按钮事件、`wx.login`、`wx.request`。
3. 微信登录：小程序拿授权码，后端换 `openid`，自动注册用户并生成 JWT。
4. 商品浏览：用户端查询分类、菜品、套餐，以及套餐内菜品列表。

其中最核心的是微信登录。商品浏览接口本身不复杂，但它依赖登录后的用户端 token，后续请求会被用户端 JWT 拦截器校验。

---

## 2. HttpClient

### 2.1 它解决什么问题

后端平时主要是“接收前端请求”。但微信登录时，后端还要主动访问微信服务器：

```text
https://api.weixin.qq.com/sns/jscode2session
```

这类“Java 代码主动发 HTTP 请求”的事情，就用 `HttpClient`。

### 2.2 GET 请求基本步骤

讲义先用测试代码演示完整流程：

```java
CloseableHttpClient httpClient = HttpClients.createDefault();
HttpGet httpGet = new HttpGet("http://localhost:8080/user/shop/status");
CloseableHttpResponse response = httpClient.execute(httpGet);
String body = EntityUtils.toString(response.getEntity());
response.close();
httpClient.close();
```

步骤可以压缩成：

```text
创建 HttpClient
创建请求对象 HttpGet / HttpPost
execute 发送请求
读取响应状态码和响应体
关闭资源
```

### 2.3 HttpClientUtil.doGet

微信登录中使用：

```java
String json = HttpClientUtil.doGet(WX_LOGIN, map);
```

它就是前面 GET 请求代码的工具类封装版。`map` 里的参数会被拼到 URL 后面：

```text
appid=xxx
secret=xxx
js_code=xxx
grant_type=authorization_code
```

最终访问微信的 `jscode2session` 接口，并返回微信服务器响应的 JSON 字符串。

---

## 3. 微信登录流程

### 3.1 为什么分两次访问微信服务器

微信登录看起来有两步都和微信服务器有关：

```text
小程序 -> 微信服务器：wx.login 获取 code
后端 -> 微信服务器：appid + secret + code 换 openid
```

必须分两步，因为 `secret` 是小程序密钥，不能放在小程序端。小程序端只能拿临时 `code`，然后把 `code` 发给自己的后端。真正换取 `openid` 的动作由后端完成。

完整流程：

```text
1. 小程序调用 wx.login() 获取临时授权码 code
2. 小程序调用 wx.request() 请求后端 /user/user/login，并携带 code
3. 后端携带 appid + secret + code 请求微信 jscode2session
4. 微信返回 openid 和 session_key
5. 后端根据 openid 查询 user 表
6. 如果 user 表没有该 openid，说明是新用户，自动注册
7. 后端用 user.id 生成 JWT token
8. 后端返回 id、openid、token 给小程序
9. 小程序保存 token，后续访问用户端接口时在请求头携带 token
```

### 3.2 关键接口

小程序请求自己的后端：

```text
POST /user/user/login
```

请求体：

```json
{
  "code": "wx.login 拿到的临时授权码"
}
```

后端请求微信：

```text
GET https://api.weixin.qq.com/sns/jscode2session
```

参数：

```text
appid
secret
js_code
grant_type=authorization_code
```

返回中最重要的是：

```text
openid
```

`openid` 是用户在当前小程序下的唯一标识。

---

## 4. 微信登录代码关系

### 4.1 配置

`application-dev.yml` 提供微信配置：

```yaml
sky:
  wechat:
    appid: 小程序appid
    secret: 小程序secret
```

`application.yml` 提供 JWT 配置：

```yaml
sky:
  jwt:
    user-secret-key: mySky
    user-ttl: 720000000000
    user-token-name: authentication
```

这些值会被 Spring Boot 绑定到配置类中：

```java
WeChatProperties
JwtProperties
```

`jwtProperties.getUserTokenName()` 决定用户端请求头的名字，当前是 `authentication`。

### 4.2 DTO / VO / Entity

`UserLoginDTO` 用来接收前端请求参数：

```java
private String code;
```

`UserLoginVO` 用来返回登录结果：

```java
private Long id;
private String openid;
private String token;
```

`User` 对应数据库 `user` 表，核心字段：

```text
id
openid
create_time
```

DTO 是入参，Entity 对应数据库表，VO 是响应数据。

### 4.3 Controller

`UserController` 的登录接口：

```java
@PostMapping("/login")
public Result<UserLoginVO> login(@RequestBody UserLoginDTO userLoginDTO)
```

完整路径由类上的路径拼出来：

```text
@RequestMapping("/user/user") + @PostMapping("/login")
= /user/user/login
```

核心动作：

```java
User user = userService.wxLogin(userLoginDTO);
claims.put(JwtClaimsConstant.USER_ID, user.getId());
String token = JwtUtil.createJWT(...);
return Result.success(userLoginVO);
```

Controller 不负责访问微信，也不负责查库注册。它只负责接收请求、调用 Service、生成 token、组装 VO。

### 4.4 Service

`UserServiceImpl.wxLogin` 是真正的微信登录业务：

```text
code -> 调微信接口 -> openid -> 查 user 表 -> 必要时 insert -> 返回 User
```

关键代码：

```java
Map<String, String> map = new HashMap<>();
map.put("appid", weChatProperties.getAppid());
map.put("secret", weChatProperties.getSecret());
map.put("js_code", userLoginDTO.getCode());
map.put("grant_type", "authorization_code");

String json = HttpClientUtil.doGet(WX_LOGIN, map);
String openid = JSON.parseObject(json).getString("openid");
```

如果 `openid == null`，说明微信登录失败，常见原因是 `appid`、`secret`、`code` 不正确。

新用户注册：

```java
User user = userMapper.getByOpenid(openid);
if (user == null) {
    user = User.builder()
            .openid(openid)
            .createTime(LocalDateTime.now())
            .build();
    userMapper.insert(user);
}
```

这里一定要写 `user = User.builder()`，否则新建出的对象没有赋值给 `user`，插入时还是 `null`。

### 4.5 Mapper 和主键回填

`UserMapper.getByOpenid`：

```java
@Select("select * from user where openid = #{openid}")
User getByOpenid(String openid);
```

`UserMapper.xml` 插入用户：

```xml
<insert id="insert" useGeneratedKeys="true" keyProperty="id">
    insert into user (openid, name, phone, sex, id_number, avatar, create_time)
    values (#{openid}, #{name}, #{phone}, #{sex}, #{idNumber}, #{avatar}, #{createTime})
</insert>
```

`useGeneratedKeys="true"` 和 `keyProperty="id"` 的作用是：数据库生成自增主键后，MyBatis 把主键回填到 `user.id`。

否则新用户插入成功后，Java 对象里的 `user.getId()` 仍然是 `null`，后面生成 JWT 时就无法把用户 id 放进 token。

---

## 5. 用户端 JWT 拦截器

### 5.1 为什么需要拦截器

登录接口只负责发 token。后续用户端接口，例如：

```text
/user/category/list
/user/dish/list
/user/setmeal/list
```

都需要知道当前用户是谁。用户端拦截器统一完成 token 校验，避免每个 Controller 重复写解析逻辑。

### 5.2 JwtTokenUserInterceptor

核心流程：

```text
判断是否 Controller 方法
从请求头读取 token
用 user-secret-key 解析 JWT
取出 USER_ID
放入 BaseContext
校验通过则放行
校验失败则返回 401
```

关键代码：

```java
String token = request.getHeader(jwtProperties.getUserTokenName());
Claims claims = JwtUtil.parseJWT(jwtProperties.getUserSecretKey(), token);
Long userId = Long.valueOf(claims.get(JwtClaimsConstant.USER_ID).toString());
BaseContext.setCurrentId(userId);
```

`BaseContext` 底层是 `ThreadLocal`，保存当前请求线程里的用户 id。

### 5.3 WebMvcConfiguration 注册

用户端拦截器必须注册后才会生效：

```java
registry.addInterceptor(jwtTokenUserInterceptor)
        .addPathPatterns("/user/**")
        .excludePathPatterns("/user/user/login")
        .excludePathPatterns("/user/shop/status");
```

为什么要放行登录接口？

```text
用户还没登录时没有 token，如果 /user/user/login 也被拦截，就永远登录不了。
```

为什么放行 `/user/shop/status`？

```text
店铺状态是小程序进入首页前就会请求的公共接口，不要求用户登录。
```

---

## 6. 商品浏览功能

### 6.1 用户端分类查询

接口：

```text
GET /user/category/list?type=1
GET /user/category/list?type=2
```

`type=1` 查询菜品分类，`type=2` 查询套餐分类。

Controller：

```java
@RestController("userCategoryController")
@RequestMapping("/user/category")
public class CategoryController {
    @GetMapping("/list")
    public Result<List<Category>> list(Integer type) {
        return Result.success(categoryService.list(type));
    }
}
```

这里复用了前面管理端分类查询的 `CategoryService.list(type)`。

### 6.2 用户端菜品查询

接口：

```text
GET /user/dish/list?categoryId=分类id
```

只查询起售中的菜品：

```java
Dish dish = new Dish();
dish.setCategoryId(categoryId);
dish.setStatus(StatusConstant.ENABLE);
List<DishVO> list = dishService.listWithFlavor(dish);
```

`DishServiceImpl.listWithFlavor` 做两件事：

```text
1. 根据分类和状态查询 dish 表
2. 遍历每个菜品，根据 dish_id 查询 dish_flavor 表，把口味放进 DishVO
```

所以返回的是 `DishVO`，不是普通 `Dish`。因为小程序展示菜品时还需要口味信息。

### 6.3 用户端套餐查询

接口：

```text
GET /user/setmeal/list?categoryId=套餐分类id
```

只查询起售套餐：

```java
Setmeal setmeal = new Setmeal();
setmeal.setCategoryId(categoryId);
setmeal.setStatus(StatusConstant.ENABLE);
List<Setmeal> list = setmealService.list(setmeal);
```

Mapper XML：

```xml
<select id="list" parameterType="Setmeal" resultType="Setmeal">
    select * from setmeal
    <where>
        <if test="name != null">
            and name like concat('%',#{name},'%')
        </if>
        <if test="categoryId != null">
            and category_id = #{categoryId}
        </if>
        <if test="status != null">
            and status = #{status}
        </if>
    </where>
</select>
```

如果小程序显示没有套餐，优先查数据库：

```sql
select count(*) from setmeal;
select id, name, category_id, status from setmeal;
select count(*) from setmeal_dish;
```

当前本地数据库的实际情况是：

```text
setmeal_count = 0
setmeal_dish_count = 0
```

分类表里有套餐分类：

```text
13 人气套餐 type=2 status=1
15 商务套餐 type=2 status=1
```

但 `setmeal` 表没有套餐数据，所以小程序显示空不是代码问题，而是数据问题。要么通过管理端新增套餐，要么手动插入测试数据。

### 6.4 套餐内菜品查询

接口：

```text
GET /user/setmeal/dish/{id}
```

Mapper：

```java
@Select("select sd.name, sd.copies, d.image, d.description " +
        "from setmeal_dish sd left join dish d on sd.dish_id = d.id " +
        "where sd.setmeal_id = #{setmealId}")
List<DishItemVO> getDishItemBySetmealId(Long setmealId);
```

这张表是套餐和菜品的中间表。没有 `setmeal_dish` 数据，即使套餐存在，点开套餐详情也查不到包含的菜品。

---

## 7. 常见错误和排查

### 7.1 小程序 console 里 ERR_CONNECTION_REFUSED

错误：

```text
POST http://localhost:8080/user/user/login net::ERR_CONNECTION_REFUSED
```

含义：

```text
8080 端口没有后端服务在监听，通常是后端没启动或启动失败。
```

处理：

```text
先看后端是否编译通过，再启动 sky-server。
```

### 7.2 wx.login 成功不代表登录成功

如果 console 里有：

```text
login:ok
code: xxx
```

只说明小程序拿到了微信临时授权码。真正登录成功还要后端 `/user/user/login` 返回 `openid` 和 `token`。

### 7.3 appid / secret 为空

如果 `application-dev.yml` 里：

```yaml
wechat:
  appid:
  secret:
```

后端请求微信时换不到 `openid`，会登录失败。

### 7.4 getUserProfile 和教程截图不同

教程较旧，现在微信对头像昵称能力做过调整。即使 `wx.getUserProfile` 能调用，也可能只得到默认头像或“微信用户”。这不影响 `wx.login` 获取 `code`，也不影响后端用 `code` 换 `openid`。

### 7.5 拦截器未注册

只写 `JwtTokenUserInterceptor` 不够，还要在 `WebMvcConfiguration` 里注册。否则 `/user/**` 请求不会经过用户端 token 校验。

### 7.6 登录接口不能被拦截

如果没有：

```java
.excludePathPatterns("/user/user/login")
```

用户没 token 就访问不了登录接口，会陷入“没登录不能登录”的问题。

### 7.7 套餐为空先查数据

套餐浏览 SQL 只查：

```text
category_id = 当前分类id
status = 1
```

如果数据库 `setmeal` 表为空，或者套餐状态是停售 `0`，小程序都会显示没有套餐。

---

## 8. 接口速查

| 功能 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 店铺状态 | GET | `/user/shop/status` | 放行，不需要 token |
| 微信登录 | POST | `/user/user/login` | 放行，使用 code 换 token |
| 分类列表 | GET | `/user/category/list?type=1/2` | 需要 token |
| 菜品列表 | GET | `/user/dish/list?categoryId=xx` | 需要 token，只查起售菜品 |
| 套餐列表 | GET | `/user/setmeal/list?categoryId=xx` | 需要 token，只查起售套餐 |
| 套餐菜品 | GET | `/user/setmeal/dish/{id}` | 需要 token，查套餐包含的菜品 |

---

## 9. 自测清单

- [ ] 能说清楚为什么 `wx.login` 和后端 `jscode2session` 要分成两步。
- [ ] 能解释 `code`、`openid`、`token` 分别是什么。
- [ ] 能说清楚 `appid`、`secret`、`user-secret-key` 分别来自哪里。
- [ ] 能解释为什么 `secret` 不能放在小程序端。
- [ ] 能画出 `/user/user/login` 从 Controller 到 Service、Mapper、微信服务器的流程。
- [ ] 能解释 `useGeneratedKeys="true"` 和 `keyProperty="id"` 为什么重要。
- [ ] 能说出用户端 JWT 拦截器从哪个请求头拿 token。
- [ ] 能解释为什么 `/user/user/login` 和 `/user/shop/status` 要放行。
- [ ] 能说清楚菜品浏览为什么返回 `DishVO` 而不是 `Dish`。
- [ ] 能说清楚套餐列表为空时应该先查 `setmeal`、`setmeal_dish` 和 `status`。
- [ ] 能用 Postman 测试 `/user/user/login`，并把小程序 `wx.login` 打印的 code 放进请求体。
- [ ] 能区分小程序拿到 `code` 成功和后端登录成功不是同一回事。
