package com.sky.mapper;

import com.sky.entity.DishFlavor;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface FlavorMapper {


    /**
     * 批量插入口味数据
     * @param flavors
     */
    void insert(@Param("flavors") List<DishFlavor> flavors);
}
