# 苍穹外卖 day03 复习笔记：菜品管理

本日主题是 **菜品管理**，核心功能包括：

1. 公共字段自动填充
2. 新增菜品和文件上传
3. 菜品分页查询
4. 删除菜品
5. 修改菜品和回显菜品

你复习时不要只背代码，要能说清楚：**前端请求进来后，Controller、Service、Mapper、XML、数据库之间怎么协作**。

---

## 1. 公共字段自动填充

### 1.1 解决什么问题

很多表都有公共字段：

```text
create_time
create_user
update_time
update_user
```

如果每个新增、修改方法里都手写：

```java
entity.setCreateTime(LocalDateTime.now());
entity.setUpdateTime(LocalDateTime.now());
entity.setCreateUser(BaseContext.getCurrentId());
entity.setUpdateUser(BaseContext.getCurrentId());
```

代码会重复很多。所以 day03 用 **AOP + 注解 + 枚举 + 反射** 统一处理。

### 1.2 整体流程

```text
Service 调用 Mapper 方法
        ↓
Mapper 方法上有 @AutoFill(OperationType.INSERT / UPDATE)
        ↓
AOP 在 Mapper 执行前拦截
        ↓
读取注解，判断是 INSERT 还是 UPDATE
        ↓
从 JoinPoint 中取出第一个参数 entity
        ↓
用反射调用 setCreateTime / setUpdateUser 等 setter
        ↓
MyBatis 执行 SQL，公共字段已经有值
```

### 1.3 需要掌握的知识点

**枚举 `OperationType`**

枚举是固定选项：

```java
INSERT
UPDATE
```

它告诉 AOP 当前是新增还是修改。新增要填 4 个字段，修改只填 2 个字段。

**注解 `@AutoFill`**

注解是给 Mapper 方法贴标签：

```java
@AutoFill(OperationType.INSERT)
void insert(Dish dish);
```

它本身不执行逻辑，真正干活的是 AOP。注解只是让 AOP 知道哪些方法需要自动填充。

**AOP**

AOP 类似一个拦截器。业务代码正常调用：

```java
dishMapper.insert(dish);
```

但执行 SQL 前，切面会先执行自动填充逻辑。

**反射**

AOP 中拿到的是：

```java
Object entity = args[0];
```

它可能是 `Dish`、`Category`、`Employee`。因为类型不固定，不能直接写：

```java
entity.setUpdateTime(now);
```

所以用反射：

```java
Method setUpdateTime = entity.getClass().getDeclaredMethod("setUpdateTime", LocalDateTime.class);
setUpdateTime.invoke(entity, now);
```

本质上等价于：

```java
dish.setUpdateTime(now);
```

### 1.4 你遇到过的重点问题

**为什么要取参数？**

```java
Object[] args = joinPoint.getArgs();
if (args == null || args.length == 0) {
    return;
}
Object entity = args[0];
```

因为自动填充必须给实体对象设置字段。MyBatis 最终从实体对象中取值写入数据库。

**能保证 `args[0]` 一定是实体对象吗？**

不是代码强制保证，而是课程里的约定：

```java
@AutoFill(...)
void insert(Entity entity);
void update(Entity entity);
```

不能乱给 `deleteById(Long id)` 这种方法加 `@AutoFill`，否则 AOP 会把 `Long` 当实体处理，反射找不到 setter。

**`e.printStackTrace()` 是什么？**

它用于打印反射失败的异常堆栈，方便知道是哪个 setter 没找到或参数类型不对。

实际项目更常用：

```java
log.error("公共字段自动填充失败", e);
```

---

## 2. 新增菜品和文件上传

### 2.1 文件上传的业务流程

新增菜品前，前端需要先上传图片。

流程：

```text
前端选择图片
        ↓
调用 /admin/common/upload
        ↓
后端接收 MultipartFile
        ↓
后端上传到阿里云 OSS
        ↓
OSS 返回可访问 URL
        ↓
后端把 URL 返回给前端
        ↓
前端新增菜品时，把 URL 放到 dish.image
```

### 2.2 为什么用阿里云 OSS

图片不适合直接存数据库，也不适合长期依赖后端服务器本地磁盘。

OSS 的作用是专门存储图片、视频等文件，后端数据库只保存文件访问路径。

要注意 OSS 前置条件：

```text
1. 开通 OSS
2. 创建 bucket
3. endpoint 必须和 bucket 所在地域一致
4. access-key-id / access-key-secret 必须有效
5. 账号需要有上传权限
6. 图片要能前端回显，bucket 或对象还要能被访问
```

你遇到过的 OSS 问题是：

```text
bucket 实际 endpoint 是 oss-cn-shenzhen.aliyuncs.com
课件配置写的是 oss-cn-hangzhou.aliyuncs.com
```

这会导致 OSS 拒绝上传。若要代码完全和课件一致，就需要使用和课件配置匹配的 OSS bucket；若使用自己的 bucket，就要改成自己的真实配置。

### 2.3 上传文件名处理

```java
String originalFilename = file.getOriginalFilename();
String extension = originalFilename.substring(originalFilename.lastIndexOf("."));
String objectName = UUID.randomUUID().toString() + extension;
String filePath = aliOssUtil.upload(file.getBytes(), objectName);
return Result.success(filePath);
```

含义：

```text
originalFilename：原始文件名，例如 a.jpg
extension：文件后缀，例如 .jpg
objectName：新的唯一文件名，避免同名文件覆盖
file.getBytes()：文件二进制内容
filePath：上传后得到的访问地址
Result.success(filePath)：把图片 URL 返回给前端
```

### 2.4 新增菜品为什么先 DTO 转 Dish

新增菜品接收的是：

```java
DishDTO
```

因为前端传来的数据不仅有 `dish` 表字段，还有：

```java
List<DishFlavor> flavors
```

口味数据属于 `dish_flavor` 表，不属于 `dish` 表。

所以 Service 中要：

```java
Dish dish = new Dish();
BeanUtils.copyProperties(dishDTO, dish);
dishMapper.insert(dish);
```

含义是：先把属于菜品表的数据拷贝到 `Dish` 实体，再插入 `dish` 表。

### 2.5 新增菜品的主键回填

```java
dishMapper.insert(dish);
Long id = dish.getId();
```

`dish.getId()` 不能凭空拿到值。因为 id 是数据库自增生成的。

Mapper XML 需要：

```xml
<insert id="insert" useGeneratedKeys="true" keyProperty="id">
```

这样 MySQL 插入后生成的 id 才会回填到 `dish.id`，后续才能：

```java
dishFlavor.setDishId(id);
```

让口味数据关联到刚新增的菜品。

---

## 3. 菜品分页查询

### 3.1 为什么接收 DTO，返回 VO

DTO 是前端传给后端的请求对象。

分页查询接收：

```java
DishPageQueryDTO
```

里面是查询条件：

```text
page
pageSize
name
categoryId
status
```

VO 是后端返回给前端展示的对象。

分页查询返回：

```java
DishVO
```

因为页面需要展示 `categoryName`，它来自 `category` 表，不是 `dish` 表原始字段。

所以：

```text
DTO：接收请求参数
VO：组织响应数据
Entity：对应数据库表
```

### 3.2 PageHelper

分页查询核心流程：

```java
PageHelper.startPage(page, pageSize);
Page<DishVO> page = dishMapper.pageQuery(dto);
return new PageResult(page.getTotal(), page.getResult());
```

`PageHelper.startPage` 会影响紧接着执行的 SQL，自动添加分页逻辑。

### 3.3 动态 SQL 判断

看到 MyBatis XML 标签就要想到动态 SQL：

```xml
<where>
<if>
<foreach>
<set>
```

分页查询里：

```xml
<if test="name != null">
    and d.name like concat('%', #{name}, '%')
</if>
```

表示条件存在才拼接 SQL。

口味批量插入里：

```xml
<foreach collection="flavors" item="df" separator=",">
```

表示集合有几个元素，SQL 就生成几组 values，所以它也是动态 SQL。

---

## 4. 删除菜品

### 4.1 业务规则

删除菜品不能直接删，要先判断：

```text
1. 菜品是否正在起售
2. 菜品是否被套餐关联
```

如果菜品起售中，不能删除。

如果菜品被套餐关联，不能删除。

删除成功时要删除两张表：

```text
dish：菜品基本信息
dish_flavor：菜品口味数据
```

### 4.2 删除流程

```text
Controller 接收 ids
        ↓
Service 遍历 ids
        ↓
查询每个菜品状态
        ↓
查询这些菜品是否被套餐关联
        ↓
删除 dish
        ↓
删除 dish_flavor
```

### 4.3 你遇到过的 MyBatis 参数名错误

报错：

```text
Parameter 'dishIds' not found. Available parameters are [ids, collection, list]
```

原因是 XML 中写：

```xml
<foreach collection="dishIds">
```

但 Mapper 方法参数没有告诉 MyBatis 它叫 `dishIds`。

解决方式一：XML 改成已有参数名：

```xml
<foreach collection="ids">
```

解决方式二：Mapper 加 `@Param`：

```java
List<Long> getSetmealIdsByDishIds(@Param("dishIds") List<Long> dishIds);
```

然后 XML 可以写：

```xml
<foreach collection="dishIds">
```

重点：**Mapper 方法参数名和 XML collection 名必须匹配**。

---

## 5. 修改菜品

修改菜品包含两个动作：

```text
1. 根据 id 查询菜品，用于页面回显
2. 提交修改，更新菜品和口味
```

### 5.1 根据 id 查询菜品

流程：

```text
GET /admin/dish/{id}
        ↓
dishMapper 查询 dish 表
        ↓
dishFlavorMapper 根据 dish_id 查询 dish_flavor 表
        ↓
组装 DishVO
        ↓
返回给前端回显
```

注意：查询口味时条件是：

```sql
where dish_id = #{dishId}
```

不是：

```sql
where id = #{id}
```

`dish_flavor.id` 是口味表自己的主键，`dish_flavor.dish_id` 才是菜品 id。

### 5.2 修改菜品

正确流程：

```text
1. DishDTO 转 Dish
2. 更新 dish 表
3. 删除旧口味
4. 插入新口味
```

参考代码：

```java
@Transactional
public void updateWithFlavor(DishDTO dishDTO) {
    Dish dish = new Dish();
    BeanUtils.copyProperties(dishDTO, dish);

    dishMapper.update(dish);

    dishFlavorMapper.deleteByDishId(dishDTO.getId());

    List<DishFlavor> flavors = dishDTO.getFlavors();
    if (flavors != null && flavors.size() > 0) {
        flavors.forEach(dishFlavor -> {
            dishFlavor.setDishId(dishDTO.getId());
        });
        dishFlavorMapper.insert(flavors);
    }
}
```

### 5.3 修改菜品易错点

**错误 1：更新方法名和 XML id 不一致**

Mapper 方法：

```java
void updateDish(Dish dish);
```

XML：

```xml
<update id="update">
```

这会导致 MyBatis 找不到对应 SQL。

要保持一致：

```java
void update(Dish dish);
```

```xml
<update id="update">
```

**错误 2：删除旧口味时误删菜品**

错误写法：

```java
dishMapper.deleteById(dish.getId());
```

这会删除 `dish` 表里的菜品。

正确写法：

```java
dishFlavorMapper.deleteByDishId(dishDTO.getId());
```

**错误 3：修改方法缺少事务**

修改菜品涉及多步数据库操作，必须加：

```java
@Transactional
```

否则可能出现菜品改了，但口味没改完整。

---

## 6. 接口文档应该怎么看

阅读接口文档时重点看：

```text
1. 请求方式：GET / POST / PUT / DELETE
2. 请求路径：/admin/dish、/admin/dish/{id}
3. 参数位置：Query、Path、Body、Header
4. 参数名和类型
5. 响应数据结构
```

### 6.1 常见参数位置

**Query 参数**

示例：

```text
DELETE /admin/dish?ids=1,2,3
```

代码：

```java
public Result delete(@RequestParam List<Long> ids)
```

**Path 参数**

示例：

```text
GET /admin/dish/70
```

代码：

```java
@GetMapping("/{id}")
public Result<DishVO> getById(@PathVariable Long id)
```

**Body 参数**

示例：新增菜品、修改菜品提交 JSON。

代码：

```java
public Result save(@RequestBody DishDTO dishDTO)
```

**Header 参数**

例如：

```text
Content-Type: application/json
token: xxx
```

`Content-Type` 通常不用业务方法手写，Spring 根据 `@RequestBody` 自动处理 JSON。

`token` 通常由拦截器处理，不在每个 Controller 方法中手动接收。

---

## 7. 本日核心代码关系

### 7.1 新增菜品

```text
DishController.saveWithFlavor
        ↓
DishService.saveWithFlavor
        ↓
DishDTO 转 Dish
        ↓
DishMapper.insert
        ↓
@AutoFill 自动填充公共字段
        ↓
dish 表插入，主键回填到 dish.id
        ↓
给每个 DishFlavor 设置 dishId
        ↓
DishFlavorMapper.insert 批量插入口味
```

### 7.2 分页查询

```text
DishController.page
        ↓
DishService.page
        ↓
PageHelper.startPage
        ↓
DishMapper.pageQuery
        ↓
dish left join category
        ↓
返回 PageResult(total, records)
```

### 7.3 删除菜品

```text
DishController.delete
        ↓
DishService.deleteBatch
        ↓
判断是否起售
        ↓
判断是否被套餐关联
        ↓
删除 dish
        ↓
删除 dish_flavor
```

### 7.4 修改菜品

```text
DishController.update
        ↓
DishService.updateWithFlavor
        ↓
DishDTO 转 Dish
        ↓
DishMapper.update
        ↓
@AutoFill 自动填充 updateTime / updateUser
        ↓
删除旧口味
        ↓
插入新口味
```

---

## 8. 复习检查清单

你复习完 day03 后，应该能回答这些问题：

```text
1. @AutoFill 为什么加在 Mapper 方法上？
2. INSERT 和 UPDATE 自动填充字段有什么区别？
3. AOP 为什么要从 JoinPoint 里拿 args[0]？
4. 反射调用 setter 的作用是什么？
5. DTO、Entity、VO 分别用于什么场景？
6. 新增菜品为什么先插 dish，再插 dish_flavor？
7. useGeneratedKeys 和 keyProperty 为什么必须配置？
8. <foreach> 为什么是动态 SQL？
9. @Param 和 XML collection 名不一致会报什么错？
10. 删除菜品前为什么要判断起售状态和套餐关联？
11. 修改菜品为什么要先删旧口味再插新口味？
12. 修改菜品为什么必须加 @Transactional？
13. 文件上传为什么要用 OSS？
14. OSS endpoint、bucket、accessKey 分别是什么？
15. 接口文档里的 Query、Path、Body、Header 参数分别对应什么代码写法？
```

---

## 9. 建议你重点回看的问题

你的问题主要集中在这几类，复习时建议优先看：

```text
1. AOP 自动填充的执行时机和参数来源
2. MyBatis XML 和 Mapper 方法名、参数名的对应关系
3. DTO / Entity / VO 的职责边界
4. 一对多表结构下的新增、删除、修改顺序
5. OSS 上传成功和 URL 可访问之间的区别
6. 修改类功能中的事务控制
```

只要这些线索打通，day03 的代码就不再是零散片段，而是一条完整的后台业务链路。
