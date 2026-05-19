package com.sky.service.impl;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.sky.constant.MessageConstant;
import com.sky.constant.StatusConstant;
import com.sky.dto.DishDTO;
import com.sky.dto.DishPageQueryDTO;
import com.sky.entity.Dish;
import com.sky.entity.DishFlavor;
import com.sky.entity.Setmeal;
import com.sky.exception.DeletionNotAllowedException;
import com.sky.mapper.DishMapper;
import com.sky.mapper.FlavorMapper;
import com.sky.mapper.SetmealDishMapper;
import com.sky.mapper.SetmealMapper;
import com.sky.result.PageResult;
import com.sky.service.DishService;
import com.sky.vo.DishVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.awt.datatransfer.FlavorMap;
import java.util.ArrayList;
import java.util.List;

@Service
@Slf4j
public class DishServiceImpl implements DishService {

    @Autowired
    private DishMapper dishMapper;
    @Autowired
    private FlavorMapper flavorMapper;
    @Autowired
    private SetmealDishMapper setmealDishMapper;
    @Autowired
    private SetmealMapper setmealMapper;
    @Autowired
    private DishService dishService;

    /**
     * 新增菜品和对应的口味
     *
     * @param dishDTO
     */
    @Transactional
    public void saveWithFlavor(DishDTO dishDTO) {
        //从 DTO 里取出属于菜品表的字段
        Dish dish = new Dish();
        BeanUtils.copyProperties(dishDTO, dish);

        //向菜品表插入1条数据
        //插入 dish 表后，把数据库生成的自增主键回填到 dish.id 里
        dishMapper.insert(dish);

        //获取insert语句生成的主键值
        Long id = dish.getId();

        List<DishFlavor> flavors = dishDTO.getFlavors();
        if(flavors != null && flavors.size() != 0){
            flavors.forEach(dishFlavor -> {
                dishFlavor.setDishId(id);
            });
            //向口味表插入n条数据
            flavorMapper.insert(flavors);
        }
    }

    /**
     * 菜品分页查询
     *
     * @param dishPageQueryDTO
     * @return
     */
    public PageResult page(DishPageQueryDTO dishPageQueryDTO) {
        PageHelper.startPage(dishPageQueryDTO.getPage(), dishPageQueryDTO.getPageSize());
        Page<DishVO> page = dishMapper.pageQuery(dishPageQueryDTO);
        return new PageResult(page.getTotal(), page.getResult());
    }

    /**
     * 按菜品id批量删除菜品请求
     *
     * @param ids
     * @return
     */
    @Override
    @Transactional
    public void delete(List<Long> ids) {
        //判断当前菜品是否能够删除---是否存在起售中的菜品？？
        for (Long id : ids){
            Dish dish = dishMapper.getDishById(id);
            if (dish.getStatus() == StatusConstant.ENABLE){
                //当前菜品处于起售中，不能删除
                throw new DeletionNotAllowedException(MessageConstant.DISH_ON_SALE);
            }
        }

        //判断当前菜品是否能够删除---是否被套餐关联了？？
        List<Long> setId = setmealDishMapper.getSetIdByDishId(ids);
        if (setId != null && setId.size() > 0){
            throw new DeletionNotAllowedException(MessageConstant.DISH_BE_RELATED_BY_SETMEAL);
        }
        //删除菜品表中的菜品数据
        for (Long DishId : ids){
            dishMapper.deleteById(DishId);
            flavorMapper.deleteByDishId(DishId);
        }
    }

    /**
     * 按菜品id查询菜品及其口味
     *
     * @param id
     * @return
     */
    @Override
    public DishVO getDishByIdWithFlavor(Long id) {
        Dish dish = dishMapper.getDishById(id);
        List<DishFlavor> dishFlavors = flavorMapper.getFlavorsById(id);

        DishVO dishVO = new DishVO();
        BeanUtils.copyProperties(dish, dishVO);
        dishVO.setFlavors(dishFlavors);
        return dishVO;
    }

    /**
     * 修改菜品及其口味
     *
     * @param dishDTO
     * @return
     */
    @Override
    @Transactional
    public void updateWithFlavor(DishDTO dishDTO) {
        //更新菜品信息
        Dish dish = new Dish();
        BeanUtils.copyProperties(dishDTO, dish);
        dishMapper.updateDish(dish);

        //删除旧口味
        flavorMapper.deleteByDishId(dishDTO.getId());

        //插入新口味
        List<DishFlavor> flavors = dishDTO.getFlavors();
        if(flavors != null && flavors.size() != 0){
            flavors.forEach(dishFlavor -> {
                dishFlavor.setDishId(dish.getId());
            });
            flavorMapper.insert(flavors);
        }
    }

    /**
     * 条件查询菜品和口味
     *
     * @param dish
     * @return
     */
    @Override
    public List<DishVO> listWithFlavor(Dish dish) {
        List<Dish> dishList = dishMapper.list(dish);
        List<DishVO> dishVOList = new ArrayList<>();

        for (Dish item : dishList) {
            DishVO dishVO = new DishVO();
            BeanUtils.copyProperties(item, dishVO);

            List<DishFlavor> flavors = flavorMapper.getFlavorsById(item.getId());
            dishVO.setFlavors(flavors);

            dishVOList.add(dishVO);
        }

        return dishVOList;
    }

    /**
     * 菜品启用停用
     *
     * @param status,id
     * @return
     */
    @Override
    @Transactional
    public void startOrStop(Integer status, Long id) {
        Dish dish = new Dish();
        dish.setStatus(status);
        dish.setId(id);
        dishMapper.updateDish(dish);

        //如果改为了禁用菜品，需要继续禁用相应套餐
        //查找套餐   修改套餐的状态值
        if (status == StatusConstant.DISABLE){
            List<Long> ids = new ArrayList<>();
            ids.add(id);
            List<Long> setIdByDishId = setmealDishMapper.getSetIdByDishId(ids);

            if (setIdByDishId != null && setIdByDishId.size() > 0){
                for (Long setId : setIdByDishId){
                    Setmeal setmeal = new Setmeal();
                    setmeal.setId(setId);
                    setmeal.setStatus(StatusConstant.DISABLE);
                    setmealMapper.update(setmeal);
                }
            }
        }

    }
}
