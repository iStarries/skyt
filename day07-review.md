# 苍穹外卖 day07 复习笔记：缓存商品与购物车

本日主线是 **缓存商品** 和 **购物车**。学习时不要只背注解和接口路径，要能说清楚：用户端读数据时为什么先走缓存，管理端改数据后为什么必须清缓存，以及购物车为什么用 `user_id` 区分不同用户的数据。

---

## 1. 当天课程主线

day07 的课程内容：

1. 缓存菜品
2. 缓存套餐
3. 添加购物车
4. 查看购物车
5. 清空购物车

对应两类能力：

- Redis 缓存：减少用户端高频查询数据库。
- 购物车：把用户选择的菜品或套餐保存到 `shopping_cart` 表。

---

## 2. 缓存菜品

### 2.1 解决什么问题

用户端小程序展示菜品时，会频繁调用：

```text
GET /user/dish/list?categoryId=xx
```

如果每次都查数据库，访问量一大，数据库压力会变高。day07 的处理方式是：按分类缓存菜品列表。

缓存 key 规则：

```text
dish_分类id
```

示例：

```text
dish_17
```

### 2.2 用户端查询流程

```text
用户端请求 /user/dish/list?categoryId=17
        -> 组装 Redis key: dish_17
        -> Redis 有数据：直接返回
        -> Redis 没数据：查数据库
        -> 查询起售中的菜品和口味
        -> 写入 Redis
        -> 返回给用户端
```

核心伪代码：

```java
String key = "dish_" + categoryId;
List<DishVO> list = (List<DishVO>) redisTemplate.opsForValue().get(key);

if (list != null && list.size() > 0) {
    return Result.success(list);
}

Dish dish = new Dish();
dish.setCategoryId(categoryId);
dish.setStatus(StatusConstant.ENABLE);
list = dishService.listWithFlavor(dish);

redisTemplate.opsForValue().set(key, list);
return Result.success(list);
```

### 2.3 管理端为什么要清缓存

只在用户端加缓存是不够的。管理端新增、修改、删除、起售停售菜品后，数据库已经变化，但 Redis 里还可能保留旧列表。

所以管理端这些方法要清理 `dish_` 开头的缓存：

```text
POST   /admin/dish
PUT    /admin/dish
DELETE /admin/dish
POST   /admin/dish/status/{status}
```

新增菜品时可以只清理当前分类：

```java
cleanCache("dish_" + dishDTO.getCategoryId());
```

修改、删除、起售停售时通常清理所有菜品分类缓存：

```java
cleanCache("dish_*");
```

---

## 3. 缓存套餐

### 3.1 Spring Cache 的作用

缓存套餐使用 Spring Cache，不再手动调用 `redisTemplate`。

启动类需要开启缓存：

```java
@EnableCaching
public class SkyApplication {
}
```

用户端套餐列表加：

```java
@Cacheable(cacheNames = "setmealCache", key = "#categoryId")
```

含义是：第一次查询某分类套餐时查数据库，并把结果放到 Redis；后续相同分类直接从缓存取。

缓存 key 形式类似：

```text
setmealCache::100
```

### 3.2 用户端查询流程

接口：

```text
GET /user/setmeal/list?categoryId=xx
```

业务条件：

```java
Setmeal setmeal = new Setmeal();
setmeal.setCategoryId(categoryId);
setmeal.setStatus(StatusConstant.ENABLE);
```

只查询起售中的套餐。

### 3.3 管理端清理套餐缓存

管理端套餐数据变化后，要用 `@CacheEvict` 清理 `setmealCache`。

新增套餐只影响一个分类，可以按分类清：

```java
@CacheEvict(cacheNames = "setmealCache", key = "#setmealDTO.categoryId")
```

删除、修改、起售停售可能影响分类列表或状态筛选，课程中使用清空所有套餐缓存：

```java
@CacheEvict(cacheNames = "setmealCache", allEntries = true)
```

对应管理端方法：

```text
POST   /admin/setmeal
DELETE /admin/setmeal
PUT    /admin/setmeal
POST   /admin/setmeal/status/{status}
```

### 3.4 管理端 SetmealController 从哪里来

day07 讲义默认管理端套餐管理已经存在。它不是 day07 第一次从零讲，而是在 day04 套餐管理实战里实现：

```text
资料/day04/项目实战-套餐管理.md
资料/day04/项目实战-套餐管理 - 参考答案.md
```

day07 只是要求在已有 `save`、`delete`、`update`、`startOrStop` 上加缓存清理注解。

---

## 4. 购物车表设计

购物车表是公共表：

```text
shopping_cart
```

不需要为每个用户单独建一张购物车表。不同用户的数据通过 `user_id` 区分。

关键字段：

```text
id
name
user_id
dish_id
setmeal_id
dish_flavor
number
amount
image
create_time
```

查询某个用户购物车：

```sql
select * from shopping_cart where user_id = 当前用户id;
```

添加购物车时通过：

```java
shoppingCart.setUserId(BaseContext.getCurrentId());
```

把当前登录用户 id 写入购物车记录。

---

## 5. 添加购物车

### 5.1 接口和 DTO

接口：

```text
POST /user/shoppingCart/add
```

DTO：

```java
public class ShoppingCartDTO implements Serializable {
    private Long dishId;
    private Long setmealId;
    private String dishFlavor;
}
```

一次请求可能添加菜品，也可能添加套餐：

- 有 `dishId`：添加菜品。
- 有 `setmealId`：添加套餐。
- 菜品可能还带 `dishFlavor`。

### 5.2 添加流程

```text
接收 ShoppingCartDTO
        -> 复制到 ShoppingCart
        -> 设置 userId 为当前登录用户
        -> 根据 userId + dishId/setmealId + dishFlavor 查询购物车
        -> 已存在：number + 1
        -> 不存在：查询菜品或套餐信息
        -> 设置 name/image/amount/number/createTime
        -> insert shopping_cart
```

关键点：

```java
List<ShoppingCart> shoppingCartList = shoppingCartMapper.list(shoppingCart);
```

这里理论上最多返回一条，但仍用 `List` 接收，因为 `list` 是通用条件查询方法，后面的“查看购物车”也复用它，只按 `userId` 查时会返回多条。

### 5.3 是否必须加事务

课程里的 `addShoppingCart` 通常没有加 `@Transactional`。原因是一次请求最终只会执行一个写操作：

```text
update shopping_cart
```

或：

```text
insert into shopping_cart
```

从课程阶段看，不加事务也能完成目标。

但要知道它有并发风险：同一个用户快速重复点击添加时，两个请求可能都查到“不存在”，然后各自插入一条重复记录。真正生产环境要考虑唯一约束、锁或数据库 upsert。

---

## 6. 查看购物车

接口：

```text
GET /user/shoppingCart/list
```

流程很简单：

```java
return shoppingCartMapper.list(
    ShoppingCart.builder()
        .userId(BaseContext.getCurrentId())
        .build()
);
```

只传 `userId`，查询当前登录用户的全部购物车记录。

---

## 7. 清空购物车

接口：

```text
DELETE /user/shoppingCart/clean
```

Service 实现：

```java
shoppingCartMapper.deleteByUserId(BaseContext.getCurrentId());
```

Mapper：

```java
@Delete("delete from shopping_cart where user_id = #{userId}")
void deleteByUserId(Long userId);
```

注意：清空购物车只删除当前用户的数据，不影响其他用户。

---

## 8. 关键代码关系

### 8.1 缓存菜品

```text
user/DishController.list
        -> RedisTemplate opsForValue().get
        -> DishService.listWithFlavor
        -> DishMapper.list
        -> FlavorMapper.getFlavorsById
        -> RedisTemplate opsForValue().set
```

管理端清缓存：

```text
admin/DishController.save/update/delete/startOrStop
        -> cleanCache("dish_*" 或 "dish_分类id")
```

### 8.2 缓存套餐

```text
user/SetmealController.list
        -> @Cacheable(setmealCache, key = categoryId)
        -> SetmealService.list
        -> SetmealMapper.list
```

管理端清缓存：

```text
admin/SetmealController.save/delete/update/startOrStop
        -> @CacheEvict(setmealCache)
```

### 8.3 购物车

```text
ShoppingCartController
        -> ShoppingCartService
        -> ShoppingCartServiceImpl
        -> ShoppingCartMapper
        -> shopping_cart
```

---

## 9. 易错点和排错

### 9.1 缓存 key 大小写要统一

用户端写缓存如果用：

```java
String key = "Dish_" + categoryId;
```

但管理端清缓存用：

```java
cleanCache("dish_*");
```

就会清不到旧缓存。课程约定是小写：

```text
dish_分类id
```

### 9.2 查询接口不应该清缓存

后台分页查询菜品或套餐只是读操作，不应该清 Redis。清缓存应该放在新增、修改、删除、起售停售这些会改变数据的接口上。

### 9.3 404 通常是接口路径缺失

前端点击菜品停售时会请求：

```text
POST /dish/status/{status}?id=xx
```

后端管理端要有：

```java
@PostMapping("/status/{status}")
```

如果 `admin/DishController` 没有这个方法，就会出现 404。

### 9.4 Mapper 方法要放对位置

更新套餐状态应该走 `SetmealMapper.update(setmeal)`，因为改的是 `setmeal` 表。

`SetmealDishMapper` 负责的是中间表 `setmeal_dish`，不应该放更新套餐主表状态的方法。

### 9.5 套餐联动停售

菜品停售时，如果某些套餐包含这个菜品，这些套餐也要停售。

流程：

```text
更新 dish.status = 0
        -> 查 setmeal_dish 中包含该 dishId 的 setmealId
        -> 更新 setmeal.status = 0
```

### 9.6 套餐起售前要检查菜品状态

套餐起售时，如果套餐内有停售菜品，不能起售套餐。

流程：

```text
根据 setmealId 查询关联菜品
        -> 有 dish.status = 0
        -> 抛出 SetmealEnableFailedException
```

### 9.7 `shopping_cart` 是公共表

不要按用户建多张购物车表。所有用户共用一张 `shopping_cart`，通过 `user_id` 区分。

---

## 10. 接口速查

### 用户端

| 功能 | 方法 | 路径 |
| --- | --- | --- |
| 查询菜品 | GET | `/user/dish/list?categoryId=xx` |
| 查询套餐 | GET | `/user/setmeal/list?categoryId=xx` |
| 添加购物车 | POST | `/user/shoppingCart/add` |
| 查看购物车 | GET | `/user/shoppingCart/list` |
| 清空购物车 | DELETE | `/user/shoppingCart/clean` |

### 管理端

| 功能 | 方法 | 路径 |
| --- | --- | --- |
| 菜品新增 | POST | `/admin/dish` |
| 菜品修改 | PUT | `/admin/dish` |
| 菜品删除 | DELETE | `/admin/dish?ids=1,2` |
| 菜品起售停售 | POST | `/admin/dish/status/{status}?id=xx` |
| 套餐新增 | POST | `/admin/setmeal` |
| 套餐修改 | PUT | `/admin/setmeal` |
| 套餐删除 | DELETE | `/admin/setmeal?ids=1,2` |
| 套餐起售停售 | POST | `/admin/setmeal/status/{status}?id=xx` |

---

## 11. 自测清单

1. 能否说出 `@Cacheable` 和 `@CacheEvict` 的区别？
2. 能否解释为什么新增套餐只清一个分类缓存，而修改套餐要清全部套餐缓存？
3. 能否说出 `dish_17` 和 `setmealCache::17` 分别代表什么？
4. 管理端修改菜品后，如果用户端仍看到旧数据，优先检查什么？
5. 为什么购物车查询方法返回 `List<ShoppingCart>`？
6. 为什么 `shopping_cart` 不需要按用户分表？
7. 清空购物车为什么必须带当前用户 id？
8. 菜品停售时，为什么可能要联动停售套餐？
9. 套餐起售时，为什么要检查套餐内菜品状态？
10. 如果前端提示 404，如何根据前端接口路径反推后端 `@RequestMapping`？
