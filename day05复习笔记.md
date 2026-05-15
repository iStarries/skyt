# Day05 复习笔记：Redis 与店铺营业状态

## 1. 今天的学习主线

Day05 的核心不是单纯背 Redis 命令，而是把 Redis 接入到苍穹外卖项目里，用它完成“店铺营业状态设置”这个功能。

学习顺序可以按这条线复习：

1. Redis 是什么，为什么适合保存访问频繁、结构简单的数据。
2. Redis 常见数据类型和命令怎么用。
3. Spring Boot 项目如何通过 Spring Data Redis 操作 Redis。
4. 店铺营业状态为什么存在 Redis，而不是数据库。
5. 管理端、用户端接口如何围绕同一个 Redis key 读写状态。
6. Knife4j 接口文档如何按管理端、用户端分组展示。

## 2. Redis 入门

Redis 是基于内存的 key-value 数据库，读写速度快，适合保存热点数据、临时状态、验证码、缓存、计数、排行榜等。

Day05 中需要重点掌握：

- Redis 服务默认端口是 `6379`。
- Windows 课程环境中通常通过 `redis-server.exe redis.windows.conf` 启动服务。
- 通过 `redis-cli.exe` 连接 Redis，默认连接本机 `127.0.0.1:6379`。
- 如果设置了密码，需要通过客户端认证后再操作。

本项目中 Redis 连接配置在 `application.yml` 和 `application-dev.yml` 中：

```yaml
spring:
  redis:
    host: ${sky.redis.host}
    port: ${sky.redis.port}
    password: ${sky.redis.password}
    database: ${sky.redis.database}
```

其中 `application-dev.yml` 提供实际环境值，例如：

```yaml
sky:
  redis:
    host: localhost
    port: 6379
    password: 123456
    database: 10
```

复习时要能回答：Spring Boot 不是直接写死 Redis 地址，而是通过配置文件注入连接信息。

## 3. Redis 五种常用数据类型

Redis 的数据类型是围绕 key 来组织的。每个 key 对应一种 value 类型。

| 类型 | 特点 | 常见场景 |
| --- | --- | --- |
| String | 最简单的字符串、数字、JSON 文本 | 验证码、开关状态、计数值 |
| Hash | 一个 key 下存多个 field-value | 对象属性、用户信息 |
| List | 有序、可重复，按插入顺序保存 | 消息队列、最近记录 |
| Set | 无序、不重复 | 标签、去重、共同好友 |
| ZSet | 不重复，每个元素带 score 并按 score 排序 | 排行榜、权重排序 |

Day05 的店铺营业状态只需要保存一个简单整数：`1` 表示营业中，`0` 表示打烊中，所以使用 String 类型最合适。

## 4. Redis 常用命令

### 4.1 String 命令

```redis
SET key value
GET key
SETEX key seconds value
SETNX key value
```

需要理解：

- `SET`：设置 key 的值。
- `GET`：获取 key 的值。
- `SETEX`：设置值并指定过期时间。
- `SETNX`：只有 key 不存在时才设置成功，常用于锁或防重复。

项目对应 Java 操作：

```java
redisTemplate.opsForValue().set("SHOP_STATUS", status);
Integer status = (Integer) redisTemplate.opsForValue().get("SHOP_STATUS");
```

### 4.2 Hash 命令

```redis
HSET key field value
HGET key field
HDEL key field
HKEYS key
HVALS key
```

Hash 适合一个 key 下保存多个属性。例如：

```redis
HSET user:100 name tom
HSET user:100 age 18
HGET user:100 name
```

Java 中通过：

```java
HashOperations hashOperations = redisTemplate.opsForHash();
```

### 4.3 List 命令

```redis
LPUSH key value1 value2
LRANGE key start stop
RPOP key
```

List 保留插入顺序，可以重复，适合队列或列表数据。

### 4.4 Set 命令

```redis
SADD key member1 member2
SMEMBERS key
SCARD key
SREM key member
```

Set 最大特点是不重复，适合去重、交集、并集。

### 4.5 ZSet 命令

```redis
ZADD key score member
ZRANGE key start stop WITHSCORES
ZINCRBY key increment member
```

ZSet 在 Set 的基础上给每个成员加 score，适合排行榜。

### 4.6 通用命令

```redis
KEYS pattern
EXISTS key
TYPE key
DEL key
```

复习重点：

- `KEYS *` 能查所有 key，但生产环境慎用。
- `EXISTS` 判断 key 是否存在。
- `TYPE` 判断 key 对应的数据类型。
- `DEL` 删除 key。

## 5. Spring Data Redis

Spring Data Redis 封装了 Redis 操作，项目中主要使用 `RedisTemplate`。

`RedisTemplate` 对不同数据类型提供了不同操作对象：

| Redis 类型 | Java 操作入口 |
| --- | --- |
| String | `opsForValue()` |
| Hash | `opsForHash()` |
| List | `opsForList()` |
| Set | `opsForSet()` |
| ZSet | `opsForZSet()` |

### 5.1 RedisConfiguration 要掌握什么

项目中的 `RedisConfiguration` 创建了一个 `RedisTemplate` Bean：

```java
@Configuration
public class RedisConfiguration {
    @Bean
    public RedisTemplate redisTemplate(RedisConnectionFactory redisConnectionFactory) {
        RedisTemplate redisTemplate = new RedisTemplate();
        redisTemplate.setConnectionFactory(redisConnectionFactory);
        redisTemplate.setKeySerializer(new StringRedisSerializer());
        return redisTemplate;
    }
}
```

关键点：

- `RedisConnectionFactory` 由 Spring Boot 根据配置文件自动创建。
- `RedisTemplate` 需要连接工厂才能连接 Redis。
- `setKeySerializer(new StringRedisSerializer())` 是为了让 Redis 中看到的 key 是正常字符串。
- 如果不设置 key 序列化器，默认可能使用 JDK 序列化，Redis 客户端中看到的 key 会变成乱码或二进制形式。

### 5.2 `@Autowired RedisTemplate` 为什么会报红

你遇到的问题：

```java
@Autowired
private RedisTemplate redisTemplate;
```

IDE 提示：

```text
Autowired members must be defined in valid Spring bean
```

原因：

- 普通 JUnit 测试类不是 Spring 容器管理的 Bean。
- 如果测试类没有启用 Spring Boot 测试上下文，`@Autowired` 不会生效。
- 此时 `redisTemplate` 运行时会是 `null`。

解决：

```java
@SpringBootTest(classes = SkyApplication.class)
public class SpringDataRedisTest {
    @Autowired
    private RedisTemplate redisTemplate;
}
```

或者课程写法：

```java
@SpringBootTest
public class SpringDataRedisTest {
}
```

复习时要记住：`@Autowired` 不是“自动 new 对象”，它依赖 Spring 容器。测试类想注入 Bean，就必须启动 Spring 测试环境。

## 6. 店铺营业状态功能

### 6.1 需求

管理端可以设置店铺营业状态：

- `1`：营业中，用户端可以下单。
- `0`：打烊中，用户端不能下单。

管理端和用户端都要查询同一个营业状态。

### 6.2 为什么存在 Redis

营业状态是一个简单、高频读取、全局唯一的状态值：

- 数据结构简单，只是 `0` 或 `1`。
- 用户端访问频繁，每次进入或下单前都可能读取。
- 不需要复杂查询。
- 放在 Redis 中读写速度快，实现也简单。

所以本功能使用 Redis 的 String 类型保存：

```text
key   = SHOP_STATUS
value = 1 或 0
```

### 6.3 接口设计

虽然管理端和用户端查询的是同一个状态，但项目约定：

- 管理端接口统一以 `/admin` 开头。
- 用户端接口统一以 `/user` 开头。

所以需要分成两个 Controller 或两个接口路径。

本功能需要掌握三个接口：

| 功能 | 请求方式 | 路径 | 说明 |
| --- | --- | --- | --- |
| 设置营业状态 | `PUT` | `/admin/shop/{status}` | 管理端设置 Redis 中的 `SHOP_STATUS` |
| 管理端查询营业状态 | `GET` | `/admin/shop/status` | 管理端读取 `SHOP_STATUS` |
| 用户端查询营业状态 | `GET` | `/user/shop/status` | 用户端读取 `SHOP_STATUS` |

### 6.4 管理端设置营业状态

核心逻辑：

```java
redisTemplate.opsForValue().set(KEY, status);
return Result.success();
```

需要理解：

- `KEY` 通常定义为常量：`SHOP_STATUS`。
- `status` 从路径变量中获取。
- 写入 Redis 后，管理端和用户端查询到的都是同一个状态。

### 6.5 查询营业状态

核心逻辑：

```java
Integer shopStatus = (Integer) redisTemplate.opsForValue().get(KEY);
return Result.success(shopStatus);
```

两个查询接口的实现几乎一样，区别只在请求路径不同。

## 7. 5.2 和 5.3 踩坑复盘

### 7.1 两个 `ShopController` 同名导致 Bean 冲突

你遇到的问题本质：

- 管理端有 `com.sky.controller.admin.ShopController`。
- 用户端有 `com.sky.controller.user.ShopController`。
- 两个类简单类名都叫 `ShopController`。
- 如果都只写 `@RestController`，Spring 默认 Bean 名都是 `shopController`。
- Spring 容器启动时会出现 Bean 名冲突。

正确写法：

```java
@RestController("adminShopController")
@RequestMapping("/admin/shop")
public class ShopController {
}
```

```java
@RestController("userShopController")
@RequestMapping("/user/shop")
public class ShopController {
}
```

复习结论：不同包下类名可以相同，但 Spring 注册 Bean 时默认 Bean 名可能相同，所以需要显式指定 Bean 名。

### 7.2 Knife4j 文档显示 `shop-controller`

如果 Controller 类上没有 `@Api(tags = "店铺相关接口")`，Knife4j 会使用默认 tag，例如 `shop-controller`。

推荐写法：

```java
@Api(tags = "店铺相关接口")
```

方法上写：

```java
@ApiOperation("设置店铺的营业状态")
```

区别：

- `@Api`：描述整个 Controller 分组。
- `@ApiOperation`：描述某个接口方法。

### 7.3 Knife4j 文档请求异常

你遇到过接口文档打开后空白，提示 Knife4j 文档请求异常。

判断思路：

1. 先访问 `http://localhost:8080/doc.html`。
   - 如果能打开页面，说明静态资源映射基本正常。
2. 再访问 `http://localhost:8080/swagger-resources`。
   - 如果能返回分组列表，说明 Knife4j 能发现 Swagger 分组。
3. 再访问带分组的文档接口：
   - `http://localhost:8080/v2/api-docs?group=管理端接口`
   - `http://localhost:8080/v2/api-docs?group=用户端接口`

注意：配置多个 `Docket` 分组后，直接访问：

```text
/v2/api-docs
```

返回 `404` 不一定是错。真正要看的是带 `group` 的地址。

如果 `swagger-resources` 能返回分组，带 `group` 的 `v2/api-docs` 也能返回 JSON，但 Knife4j 页面还是空白，可以尝试：

```javascript
localStorage.clear()
sessionStorage.clear()
location.reload()
```

或者使用浏览器无痕窗口重新访问 `doc.html`。原因可能是 Knife4j 前端缓存了旧分组名。

### 7.4 Docket 分组配置

5.3 的核心代码是定义两个 `Docket`：

```java
@Bean
public Docket docket1() {
    return new Docket(DocumentationType.SWAGGER_2)
            .groupName("管理端接口")
            .apiInfo(apiInfo)
            .select()
            .apis(RequestHandlerSelectors.basePackage("com.sky.controller.admin"))
            .paths(PathSelectors.any())
            .build();
}
```

```java
@Bean
public Docket docket2() {
    return new Docket(DocumentationType.SWAGGER_2)
            .groupName("用户端接口")
            .apiInfo(apiInfo)
            .select()
            .apis(RequestHandlerSelectors.basePackage("com.sky.controller.user"))
            .paths(PathSelectors.any())
            .build();
}
```

要点：

- `groupName` 决定 Knife4j 左上角分组名称。
- `basePackage("com.sky.controller.admin")` 只扫描管理端 Controller。
- `basePackage("com.sky.controller.user")` 只扫描用户端 Controller。
- 分组名变了以后，旧缓存可能还请求旧分组地址。

## 8. Day05 最容易混淆的点

### 8.1 RedisTemplate 和 Redis 命令的对应关系

| Redis 命令 | Java 写法 |
| --- | --- |
| `SET key value` | `redisTemplate.opsForValue().set(key, value)` |
| `GET key` | `redisTemplate.opsForValue().get(key)` |
| `SETEX key seconds value` | `redisTemplate.opsForValue().set(key, value, timeout, TimeUnit.SECONDS)` |
| `SETNX key value` | `redisTemplate.opsForValue().setIfAbsent(key, value)` |
| `HSET key field value` | `redisTemplate.opsForHash().put(key, field, value)` |
| `HGET key field` | `redisTemplate.opsForHash().get(key, field)` |
| `KEYS *` | `redisTemplate.keys("*")` |
| `EXISTS key` | `redisTemplate.hasKey(key)` |
| `TYPE key` | `redisTemplate.type(key)` |
| `DEL key` | `redisTemplate.delete(key)` |

### 8.2 编译通过不代表 Spring 启动一定通过

比如两个 `ShopController` 默认 Bean 名冲突：

- Java 编译可能通过。
- Maven compile 也可能通过。
- 但 Spring 容器启动时会报 Bean 注册冲突。

所以排查 Spring 项目问题时，要区分：

- 编译期问题：语法、类型、依赖。
- 启动期问题：Bean 冲突、配置错误、数据库/Redis 连接失败。
- 运行期问题：接口路径、参数、业务逻辑。
- 文档生成问题：Swagger/Knife4j 配置、分组、缓存。

### 8.3 业务接口正常不代表 Knife4j 正常

你这次遇到的 Knife4j 问题就是典型例子：

- 前后端联调正常。
- Redis 数据能正常写入。
- 业务接口没有问题。
- 但 Knife4j 页面可能因为分组、缓存、文档接口地址问题显示异常。

排查时不要把“业务接口正常”和“文档页面正常”混为一谈。

## 9. 自测题

### 9.1 Redis 基础

1. Redis 默认端口是多少？
2. String、Hash、List、Set、ZSet 分别适合什么场景？
3. `SETEX` 和 `SETNX` 的区别是什么？
4. `KEYS *` 为什么不建议在生产环境频繁使用？
5. `TYPE key` 能解决什么排查问题？

### 9.2 Spring Data Redis

1. `RedisTemplate` 是谁创建的？
2. `RedisConnectionFactory` 的连接信息来自哪里？
3. 为什么要设置 `StringRedisSerializer`？
4. `opsForValue()` 对应 Redis 的哪种数据类型？
5. 测试类中 `@Autowired RedisTemplate` 报红，根本原因是什么？

### 9.3 店铺营业状态

1. 为什么店铺营业状态适合存 Redis？
2. `SHOP_STATUS` 的 value 为什么用 `0` 和 `1`？
3. 管理端和用户端查询的是同一个状态，为什么还要分两个接口？
4. 设置营业状态接口的请求路径和请求方式是什么？
5. 用户端查询营业状态接口的请求路径和请求方式是什么？

### 9.4 Knife4j

1. `Docket` 的作用是什么？
2. `groupName` 影响 Knife4j 的哪个地方？
3. `RequestHandlerSelectors.basePackage` 的作用是什么？
4. 多个 `Docket` 后，为什么 `/v2/api-docs` 可能返回 404？
5. 如果 `doc.html` 空白，应该依次检查哪几个地址？

## 10. 复习 checklist

- [ ] 能独立启动 Redis 并用客户端连接。
- [ ] 能说出五种 Redis 数据类型的特点。
- [ ] 能写出 String、Hash、通用命令的基本用法。
- [ ] 能解释 `RedisTemplate` 的作用。
- [ ] 能解释为什么配置 key 序列化器。
- [ ] 能修复测试类中 `@Autowired` 不生效的问题。
- [ ] 能画出店铺营业状态的读写流程。
- [ ] 能说清楚管理端和用户端为什么分接口。
- [ ] 能排查两个同名 Controller 的 Bean 冲突。
- [ ] 能排查 Knife4j 文档请求异常。

## 11. 推荐复习顺序

第一遍按业务流程复习：

```text
前端点击营业状态 -> 管理端接口 -> Redis 写入 SHOP_STATUS -> 管理端/用户端读取 SHOP_STATUS
```

第二遍按技术栈复习：

```text
Redis 命令 -> RedisTemplate -> Controller 接口 -> Knife4j 文档
```

第三遍按问题复盘：

```text
@Autowired 报红 -> 同名 Controller Bean 冲突 -> Knife4j 文档空白
```

如果能把这三条线都讲清楚，Day05 就基本掌握了。
