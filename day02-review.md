# 苍穹外卖 day02 复习笔记：员工管理

出处：day02 / 讲义 / 苍穹外卖-day02.md；day02 / 接口文档 / 苍穹外卖-管理端接口.html；源码 / EmployeeController.java

本日员工管理主线包括：

1. 新增员工
2. 员工分页查询
3. 启用禁用员工账号
4. 编辑员工，包括回显和修改

复习时不要只记某个注解怎么写，要能说清楚：**前端页面需要一个功能，后端如何从接口文档拆出请求方式、路径、参数来源，再经过 Controller、Service、Mapper、XML、数据库完成业务。**

---

## 1. 当天课程主线

Day02 的员工管理功能围绕 `employee` 表展开。核心字段包括：

```text
id           主键
name         姓名
username     登录账号，唯一
password     密码
phone        手机号
sex          性别
id_number    身份证号
status       账号状态，1 正常，0 锁定
create_time  创建时间
update_time  修改时间
create_user  创建人 id
update_user  修改人 id
```

后端分层关系：

```text
前端请求
        ↓
EmployeeController
        ↓
EmployeeService / EmployeeServiceImpl
        ↓
EmployeeMapper
        ↓
EmployeeMapper.xml 或 Mapper 注解 SQL
        ↓
employee 表
        ↓
Result / PageResult 返回前端
```

各层职责：

```text
Controller：接请求、取参数、调用 Service、返回 Result
Service：写业务规则，补默认值、时间、当前操作人
Mapper：定义数据库操作方法
XML：写复杂动态 SQL
DTO：接收前端传入参数
Entity：对应数据库表
Result / PageResult：统一响应格式
```

---

## 2. 核心功能流程

### 2.1 新增员工

接口：

```text
POST /admin/employee
Content-Type: application/json
```

Controller：

```java
@PostMapping
public Result save(@RequestBody EmployeeDTO employeeDTO) {
    employeeService.save(employeeDTO);
    return Result.success();
}
```

这几个点要分清楚：

```text
@PostMapping：把方法注册为 POST 接口
@RequestBody：从请求体 JSON 中读取参数，转成 EmployeeDTO
EmployeeDTO：只接收前端传来的员工表单字段
Result.success()：告诉前端操作成功
```

Service 新增员工时要补充后端字段：

```java
Employee employee = new Employee();
BeanUtils.copyProperties(employeeDTO, employee);

employee.setPassword(DigestUtils.md5DigestAsHex(PasswordConstant.DEFAULT_PASSWORD.getBytes()));
employee.setStatus(StatusConstant.ENABLE);
employee.setCreateTime(LocalDateTime.now());
employee.setUpdateTime(LocalDateTime.now());
employee.setCreateUser(BaseContext.getCurrentId());
employee.setUpdateUser(BaseContext.getCurrentId());

employeeMapper.insert(employee);
```

为什么不用前端直接传完整 `Employee`：

```text
前端只应该提交 username、name、phone、sex、idNumber 等表单字段。
password、status、createTime、createUser 这些字段应该由后端控制。
```

Mapper 插入：

```java
@Insert("insert into employee (...) values (...)")
void insert(Employee employee);
```

注意：调用时是小写对象名：

```java
employeeMapper.insert(employee);   // 对
EmployeeMapper.insert(employee);   // 错，EmployeeMapper 是接口类型
```

### 2.2 员工分页查询

接口：

```text
GET /admin/employee/page?page=1&pageSize=10&name=张三
```

分页查询的参数是 Query，不是 JSON。参数在 URL 后面：

```text
?page=1&pageSize=10&name=张三
```

Controller：

```java
@GetMapping("/page")
public Result<PageResult> page(EmployeePageQueryDTO employeePageQueryDTO) {
    PageResult pageResult = employeeService.pageQuery(employeePageQueryDTO);
    return Result.success(pageResult);
}
```

这里不写 `@RequestBody`，因为参数不是 JSON body，而是 query 参数。Spring MVC 会把 query 参数封装进 `EmployeePageQueryDTO`。

Service：

```java
PageHelper.startPage(employeePageQueryDTO.getPage(), employeePageQueryDTO.getPageSize());
Page<Employee> page = employeeMapper.pageQuery(employeePageQueryDTO);

long total = page.getTotal();
List<Employee> records = page.getResult();

return new PageResult(total, records);
```

分页返回结果：

```text
total：符合查询条件的总记录数
records：当前页的数据集合
```

例如：

```json
{
  "total": 4,
  "records": [
    { "id": 7, "username": "xiaolei" },
    { "id": 3, "username": "zhangfei" }
  ]
}
```

含义是：符合条件的记录总数是 4，但当前页只返回 2 条，因为 `pageSize = 2`。

XML：

```xml
<select id="pageQuery" resultType="com.sky.entity.Employee">
    select * from employee
    <where>
        <if test="name != null and name != ''">
            and name like concat('%', #{name}, '%')
        </if>
    </where>
    order by create_time desc
</select>
```

### 2.3 启用禁用员工账号

接口：

```text
POST /admin/employee/status/{status}?id=3
```

示例：

```text
POST /admin/employee/status/0?id=3  禁用 id=3 的员工
POST /admin/employee/status/1?id=3  启用 id=3 的员工
```

Controller：

```java
@PostMapping("/status/{status}")
public Result startOrStop(@PathVariable Integer status, Long id) {
    employeeService.startOrStop(status, id);
    return Result.success();
}
```

参数来源：

```text
@PathVariable Integer status：从路径 /status/{status} 中取值
Long id：从 query 参数 ?id=3 中取值
```

为什么用 POST，不用 GET：

```text
GET 语义是查询数据，不应该修改服务器状态。
启用禁用会 update employee set status = ?，属于修改操作。
课程接口文档约定使用 POST。
```

Service：

```java
Employee employee = Employee.builder()
        .id(id)
        .status(status)
        .build();

employeeMapper.update(employee);
```

这里创建 `Employee` 不是新增员工，而是借它装两个字段：

```text
id：要修改哪一行
status：要改成启用还是禁用
```

### 2.4 编辑员工：回显和修改

编辑员工分两个接口。

第一个接口：根据 id 查询员工信息，用于回显。

```text
GET /admin/employee/{id}
```

Controller：

```java
@GetMapping("/{id}")
public Result<Employee> getById(@PathVariable Long id) {
    Employee employee = employeeService.getById(id);
    return Result.success(employee);
}
```

前端点击修改后的流程：

```text
点击修改
        ↓
前端拿到当前行员工 id
        ↓
跳转 /employee/add?id=员工id
        ↓
调用 GET /employee/{id}
        ↓
后端返回员工数据
        ↓
前端 this.ruleForm = res.data.data
        ↓
v-model="ruleForm.xxx" 的表单自动显示数据
```

第二个接口：提交修改。

```text
PUT /admin/employee
Content-Type: application/json
```

Controller：

```java
@PutMapping
public Result update(@RequestBody EmployeeDTO employeeDTO) {
    employeeService.update(employeeDTO);
    return Result.success();
}
```

为什么用 PUT：

```text
编辑员工是在更新已有员工资源。
请求体里带 id 和新的员工信息，语义是把这个员工更新为新的数据。
```

Service 正确顺序：

```java
Employee employee = new Employee();
BeanUtils.copyProperties(employeeDTO, employee);

employee.setUpdateUser(BaseContext.getCurrentId());
employee.setUpdateTime(LocalDateTime.now());

employeeMapper.update(employee);
```

必须先设置 `updateUser`、`updateTime`，再调用 `employeeMapper.update(employee)`。如果先执行 update，再 set 时间和修改人，只是改了 Java 内存对象，数据库不会变化。

---

## 3. 关键代码关系

### 3.1 请求方式和参数位置

| 场景 | 请求方式 | 参数位置 | 后端写法 |
| --- | --- | --- | --- |
| 新增员工 | POST | JSON body | `@RequestBody EmployeeDTO` |
| 分页查询 | GET | query | `EmployeePageQueryDTO` |
| 启用禁用 | POST | path + query | `@PathVariable Integer status, Long id` |
| 根据 id 查询 | GET | path | `@PathVariable Long id` |
| 编辑员工 | PUT | JSON body | `@RequestBody EmployeeDTO` |

记忆方式：

```text
查数据：GET
新增：POST
修改已有资源：PUT
路径里的 {xxx}：@PathVariable
URL 后面的 ?xxx=：query 参数
请求体 JSON：@RequestBody
```

### 3.2 Mapper 接口和 XML 的绑定关系

Mapper 接口：

```java
void update(Employee employee);
Page<Employee> pageQuery(EmployeePageQueryDTO employeePageQueryDTO);
```

XML 必须对应：

```xml
<update id="update" parameterType="Employee">
<select id="pageQuery" resultType="com.sky.entity.Employee">
```

规则：

```text
Mapper 接口方法名 = XML 标签 id
Mapper 接口全限定名 = XML namespace
```

如果接口写：

```java
void updateStatus(Employee employee);
```

但 XML 写：

```xml
<update id="update">
```

就会报：

```text
Invalid bound statement (not found): com.sky.mapper.EmployeeMapper.updateStatus
```

### 3.3 动态 update 的意义

XML：

```xml
<update id="update" parameterType="Employee">
    update employee
    <set>
        <if test="name != null">name = #{name},</if>
        <if test="username != null">username = #{username},</if>
        <if test="password != null">password = #{password},</if>
        <if test="phone != null">phone = #{phone},</if>
        <if test="sex != null">sex = #{sex},</if>
        <if test="idNumber != null">id_number = #{idNumber},</if>
        <if test="updateTime != null">update_time = #{updateTime},</if>
        <if test="updateUser != null">update_user = #{updateUser},</if>
        <if test="status != null">status = #{status},</if>
    </set>
    where id = #{id}
</update>
```

作用：

```text
哪个属性不为 null，就更新哪个字段。
启用禁用只传 id/status，就只更新 status。
编辑员工传 id/name/phone 等，就更新这些字段。
```

`where id = #{id}` 的 id 来自传入的 `Employee` 对象：

```text
#{id} 等价于 employee.getId()
```

`<set>` 会自动处理最后多余的逗号，避免 SQL 变成：

```sql
set status = ?,
```

### 3.4 当前登录人 id

登录时，后端把员工 id 放入 JWT：

```java
claims.put(JwtClaimsConstant.EMP_ID, employee.getId());
```

后续请求带 token，拦截器解析：

```java
Claims claims = JwtUtil.parseJWT(jwtProperties.getAdminSecretKey(), token);
Long empId = Long.valueOf(claims.get(JwtClaimsConstant.EMP_ID).toString());
BaseContext.setCurrentId(empId);
```

Service 中读取：

```java
BaseContext.getCurrentId()
```

用于设置：

```text
create_user
update_user
```

ThreadLocal 的作用：

```text
同一个请求通常由同一个线程处理。
拦截器先把 empId 放入当前线程的 ThreadLocal。
Service 在同一线程中取出 empId。
```

---

## 4. 重要知识点

### 4.1 Spring MVC 自动封装参数

看到：

```java
public Result save(@RequestBody EmployeeDTO employeeDTO)
```

说明 Spring MVC 会把请求体 JSON 转成 `EmployeeDTO`。这个过程由消息转换器和 Jackson 完成。

`@RequestBody` 是请求体，`@ResponseBody` 是响应体。参数前面应该用 `@RequestBody`，不是 `@ResponseBody`。

### 4.2 employeeService 是怎么来的

Controller 中：

```java
@Autowired
private EmployeeService employeeService;
```

Service 实现类：

```java
@Service
public class EmployeeServiceImpl implements EmployeeService
```

Spring 会创建 `EmployeeServiceImpl` 对象，并注入给 `EmployeeController`。变量类型写接口 `EmployeeService`，实际对象是实现类 `EmployeeServiceImpl`。

### 4.3 Result 和 PageResult

`Result` 是统一响应：

```json
{
  "code": 1,
  "msg": null,
  "data": {}
}
```

`PageResult` 是分页数据：

```json
{
  "total": 4,
  "records": []
}
```

新增、修改、启用禁用通常只需要返回：

```java
return Result.success();
```

分页查询需要返回：

```java
return Result.success(pageResult);
```

### 4.4 WebMvcConfiguration 和时间格式

分页列表中 `LocalDateTime` 如果直接用默认转换，可能返回：

```json
[2026, 5, 7, 17, 21, 39]
```

课程通过扩展消息转换器统一处理时间格式：

```java
@Override
protected void extendMessageConverters(List<HttpMessageConverter<?>> converters) {
    MappingJackson2HttpMessageConverter converter = new MappingJackson2HttpMessageConverter();
    converter.setObjectMapper(new JacksonObjectMapper());
    converters.add(0, converter);
}
```

`protected` 是因为它重写的是父类 `WebMvcConfigurationSupport` 的扩展方法，不是给 Controller 或 Service 外部调用的业务接口。

---

## 5. 易错点和排错

### 5.1 Swagger 看不到接口

如果方法只有：

```java
@ApiOperation("新增员工")
public Result save(...)
```

Swagger 不会把它识别为接口。必须有 Spring MVC 映射注解：

```java
@PostMapping
@GetMapping
@PutMapping
```

`@ApiOperation` 只是接口文档说明，不负责注册路由。

### 5.2 前后端联调报 Request method 'POST' not supported

含义：

```text
前端发了 POST，但后端这个路径没有 POST 接口。
```

常见原因：

```java
@GetMapping("/status/{status}")   // 错
@PostMapping("/status/{status}")  // 对
```

Swagger 能调通不代表前后端一定能通。要确认 Swagger 使用的请求方式和前端代码一致。

### 5.3 Swagger 返回 400 Bad Request

编辑员工时，`idNumber` 是字符串：

```java
private String idNumber;
```

JSON 中要写：

```json
"idNumber": "341212199912121212"
```

不要写成：

```json
"idNumber": 341212199912121212
```

手机号、身份证号都应该作为字符串传递。

### 5.4 用户名重复异常

`username` 有唯一约束，重复插入时数据库会抛：

```java
SQLIntegrityConstraintViolationException
```

不需要专门在 `exception` 包里新建异常类，因为这个异常已经由数据库/JDBC 抛出。课程做法是在 `GlobalExceptionHandler` 中统一捕获，转成前端友好提示：

```java
@ExceptionHandler
public Result exceptionHandler(SQLIntegrityConstraintViolationException ex) {
    String message = ex.getMessage();
    if (message.contains("Duplicate entry")) {
        String[] split = message.split(" ");
        String username = split[2];
        return Result.error(username + MessageConstant.ALREADY_EXISTS);
    }
    return Result.error(MessageConstant.UNKNOWN_ERROR);
}
```

职责区分：

```text
exception 包：定义业务异常类型
GlobalExceptionHandler：捕获异常，并转换成 Result.error(...)
```

### 5.5 修改时间没有更新

错误顺序：

```java
employeeMapper.update(employee);
employee.setUpdateUser(BaseContext.getCurrentId());
employee.setUpdateTime(LocalDateTime.now());
```

这只是在 SQL 执行后修改了 Java 对象，不会影响数据库。

正确顺序：

```java
employee.setUpdateUser(BaseContext.getCurrentId());
employee.setUpdateTime(LocalDateTime.now());
employeeMapper.update(employee);
```

### 5.6 MyBatis 日志怎么看

日志：

```text
Preparing: update employee SET name = ?, username = ? where id = ?
Parameters: zhangfei(String), 张飞(String), 3(Long)
Updates: 1
```

含义：

```text
Preparing：最终 SQL，? 是占位符
Parameters：每个 ? 对应的真实参数
Updates：影响了几行，1 表示成功更新一行
```

分页 count 日志中的：

```text
Total: 1
```

不一定表示查到 1 条员工，它可能只是说明 `count` 查询返回了 1 行结果。真正要看接口响应里的 `data.total`。

### 5.7 日志占位符写法

错误：

```java
log.info("当前员工id：", empId);
```

正确：

```java
log.info("当前员工id：{}", empId);
```

---

## 6. 接口文档阅读要点

实现功能前，先从接口文档确认四件事：

```text
Path：完整请求路径
Method：GET / POST / PUT
Parameters：参数在哪里，叫什么，类型是什么
Response：返回给前端的数据结构
```

例如分页查询：

```text
Path：/admin/employee/page
Method：GET
参数：page、pageSize、name，Query
返回：Result<PageResult>
```

因为类上有：

```java
@RequestMapping("/admin/employee")
```

方法上只写剩下的：

```java
@GetMapping("/page")
```

路径拼接：

```text
/admin/employee + /page = /admin/employee/page
```

实现一个前端需要的业务功能时，按这个流程走：

```text
1. 看产品页面或前端需求，明确用户要做什么
2. 看接口文档，确认 Method、Path、参数、返回值
3. 设计 DTO 或确认简单参数来源
4. 写 Controller，接参数并返回 Result
5. 在 Service 接口声明业务方法
6. 在 ServiceImpl 中写业务规则
7. 在 Mapper 接口声明数据库方法
8. 用注解 SQL 或 XML 写数据库操作
9. 用 Swagger 测试后端接口
10. 前后端联调，检查请求方式、路径、参数名、token、返回字段
```

后端是在服务前端页面需求，但不是只做转发。后端还要负责：

```text
参数接收和转换
业务默认值
登录状态和当前操作人
数据库约束和异常处理
统一响应格式
数据安全和一致性
```

---

## 7. 复习检查清单

学完 Day02 后，你应该能回答这些问题：

- `@PostMapping`、`@GetMapping`、`@PutMapping` 分别适合什么场景？
- `@RequestBody`、`@PathVariable`、query 参数分别从哪里取值？
- 为什么新增员工用 `EmployeeDTO`，不直接用 `Employee`？
- `employeeService` 是谁创建的？为什么 Controller 可以直接注入？
- `employeeMapper.update(employee)` 为什么能同时支持启用禁用和编辑员工？
- XML 里的 `where id = #{id}` 从哪里取到 id？
- Mapper 方法名和 XML 的 `id` 不一致会报什么错？
- `PageResult.total` 和 `records` 分别是什么意思？
- 为什么接口返回成功还要写 `return Result.success()`？
- 用户名重复为什么在 `GlobalExceptionHandler` 中处理？
- 当前登录员工 id 如何从 JWT 传到 Service？
- 为什么 `updateTime` 必须在调用 Mapper 前设置？
- Swagger 能调通但前端失败时，优先检查哪些内容？

最重要的一句话：

```text
一个业务功能不是某个方法单独完成的，而是接口文档、Controller、DTO、Service、Mapper、XML、数据库和前端约定共同组成的一条链路。
```
