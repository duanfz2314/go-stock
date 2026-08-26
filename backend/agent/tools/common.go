package tools

import (
	"strings"

	"go-stock/backend/data"
)

// @Author spark
// @Date 2025/8/5 17:20
// @Desc
//-----------------------------------------------------------------------------------

// GetStockCode 将 AI/用户传入的股票代码归一化为内部前缀格式（小写）。
// 委托 data.NormalizeStockCode，与自选、分组、行情接口使用同一套规则，避免空串 panic、
// 港股 5 位代码被误判为深市、美股 us 前缀未转 gb_ 等问题。
func GetStockCode(dcCode string) string {
	return data.NormalizeStockCode(dcCode)
}

// normalizeToolStockCodes 归一化工具参数中的股票代码列表，去空并按归一化结果去重。
func normalizeToolStockCodes(codes []string) []string {
	if len(codes) == 0 {
		return codes
	}
	out := make([]string, 0, len(codes))
	seen := make(map[string]struct{}, len(codes))
	for _, c := range codes {
		n := GetStockCode(strings.TrimSpace(c))
		if n == "" {
			continue
		}
		if _, ok := seen[n]; ok {
			continue
		}
		seen[n] = struct{}{}
		out = append(out, n)
	}
	return out
}

// isHKOrUSCode 判断归一化后的代码是否应走港股/美股数据路径。
func isHKOrUSCode(code string) bool {
	return strings.HasPrefix(code, "hk") || strings.HasPrefix(code, "us") || strings.HasPrefix(code, "gb_")
}
