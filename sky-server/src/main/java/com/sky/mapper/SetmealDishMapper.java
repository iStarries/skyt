package com.sky.mapper;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface SetmealDishMapper {

    /**
     * 按菜品id查找菜品被哪些套餐需要
     *
     * @param ids
     * @return
     */
    List<Long> getSetIdByDishId(List<Long> ids);
}
