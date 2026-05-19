package com.sky.service;

import com.sky.dto.ShoppingCartDTO;

public interface ShoppingCardService {

    /**
     * 添加购物车
     * @param shoppingCartDTO
     * @return
     */
    void add(ShoppingCartDTO shoppingCartDTO);
}
