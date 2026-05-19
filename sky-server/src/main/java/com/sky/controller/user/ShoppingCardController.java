package com.sky.controller.user;

import com.sky.dto.ShoppingCartDTO;
import com.sky.entity.ShoppingCart;
import com.sky.result.Result;
import com.sky.service.ShoppingCardService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@Slf4j
@RequestMapping("/user/shoppingCart")
@Api(tags = "Shopping cart APIs")
public class ShoppingCardController {

    @Autowired
    private ShoppingCardService shoppingCardService;

    @PostMapping("/add")
    @ApiOperation("Add shopping cart item")
    public Result add(@RequestBody ShoppingCartDTO shoppingCartDTO) {
        log.info("Add shopping cart item: {}", shoppingCartDTO);
        shoppingCardService.add(shoppingCartDTO);
        return Result.success();
    }

    @GetMapping("/list")
    @ApiOperation("List shopping cart items")
    public Result<List<ShoppingCart>> list() {
        log.info("List shopping cart items");
        return Result.success(shoppingCardService.showShoppingCart());
    }

    @DeleteMapping("/clean")
    @ApiOperation("Clean shopping cart")
    public Result clean() {
        log.info("Clean shopping cart");
        shoppingCardService.cleanShoppingCart();
        return Result.success();
    }
}
