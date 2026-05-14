package com.sky.service;

import com.sky.dto.DishDTO;
import com.sky.dto.DishPageQueryDTO;
import com.sky.result.PageResult;
import com.sky.vo.DishVO;

import java.util.List;

public interface DishService {

    /**
     * 新增菜品和对应的口味
     *
     * @param dishDTO
     */
    void saveWithFlavor(DishDTO dishDTO);

    /**
     * 菜品分页查询
     *
     * @param dishPageQueryDTO
     * @return
     */
    PageResult page(DishPageQueryDTO dishPageQueryDTO);

    /**
     * 按菜品id批量删除菜品请求
     *
     * @param ids
     * @return
     */
    void delete(List<Long> ids);

    /**
     * 按菜品id查询菜品及其口味
     *
     * @param id
     * @return
     */
    DishVO getDishByIdWithFlavor(Long id);

    /**
     * 修改菜品及其口味
     *
     * @param dishDTO
     * @return
     */
    void updateWithFlavor(DishDTO dishDTO);
}
