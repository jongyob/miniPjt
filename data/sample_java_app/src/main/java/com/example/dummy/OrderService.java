package com.example.dummy;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

/**
 * 코드 품질 점검 Agent 실습용 더미 소스.
 */
public class OrderService {

    private final Connection connection;

    public OrderService(Connection connection) {
        this.connection = connection;
    }

    // 성능 위반(의도적): 주문 ID 목록을 한 번에 조회하지 않고, 반복문 안에서 매번 새 쿼리를 던짐 (N+1)
    public List<String> getOrderProductNames(List<Long> orderIds) throws Exception {
        List<String> productNames = new ArrayList<>();
        Statement statement = connection.createStatement();

        for (Long orderId : orderIds) {
            String query = "SELECT product_name FROM order_items WHERE order_id = " + orderId;
            ResultSet rs = statement.executeQuery(query);
            if (rs.next()) {
                productNames.add(rs.getString("product_name"));
            }
        }
        return productNames;
    }
}
