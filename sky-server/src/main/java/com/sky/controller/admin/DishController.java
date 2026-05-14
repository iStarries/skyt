package com.sky.controller.admin;


import com.sky.dto.DishDTO;
import com.sky.dto.DishPageQueryDTO;
import com.sky.result.PageResult;
import com.sky.result.Result;
import com.sky.service.DishService;
import com.sky.vo.DishVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/admin/dish")
@Slf4j
@Api(tags = "菜品相关借口")
public class DishController {

    @Autowired
    private DishService dishService;

    /**
     * 新增菜品
     *
     * @param dishDTO
     * @return
     */
    @PostMapping
    @ApiOperation("新增菜品")
    public Result saveWithFlavor(@RequestBody DishDTO dishDTO){
        log.info("新增菜品：{}", dishDTO);
        dishService.saveWithFlavor(dishDTO);
        return Result.success();
    }

    /**
     * 菜品分页查询
     *
     * @param dishPageQueryDTO
     * @return
     */
    @GetMapping("/page")
    @ApiOperation("菜品分页查询")
    public Result<PageResult> page(DishPageQueryDTO dishPageQueryDTO){
        log.info("菜品分页查询请求：{}", dishPageQueryDTO);
        PageResult pageResult = dishService.page(dishPageQueryDTO);
        return Result.success(pageResult);
    }

    /**
     * 按菜品id批量删除菜品请求
     *
     * @param ids
     * @return
     */
    @DeleteMapping
    @ApiOperation("按菜品id批量删除菜品请求")
    public Result delete(@RequestParam List<Long> ids){
        log.info("按菜品id批量删除菜品请求：{}", ids);
        dishService.delete(ids);
        return Result.success();
    }

    /**
     * 按菜品id查询菜品及其口味
     *
     * @param id
     * @return
     */
    @GetMapping("/{id}")
    @ApiOperation("按菜品id查询菜品及其口味")
    public Result<DishVO> getDishByIdWithFlavor(@PathVariable Long id){
        log.info("按菜品id查询菜品及其口味:{}", id);
        DishVO dishVO = dishService.getDishByIdWithFlavor(id);
        return Result.success(dishVO);
    }

    /**
     * 修改菜品及其口味
     *
     * @param dishDTO
     * @return
     */
    @PutMapping
    @ApiOperation("修改菜品及其口味")
    public Result update(@RequestBody DishDTO dishDTO){
        log.info("修改菜品及其口味：{}", dishDTO);
        dishService.updateWithFlavor(dishDTO);
        return Result.success();
    }

}
