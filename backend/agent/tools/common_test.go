package tools

import "testing"

func TestGetStockCode(t *testing.T) {
	cases := []struct {
		in, want string
	}{
		{"", ""},
		{"  ", ""},
		{"600938.SH", "sh600938"},
		{"600938", "sh600938"},
		{"sh600938", "sh600938"},
		{"SH600938", "sh600938"},
		{"000756.SZ", "sz000756"},
		{"000001", "sz000001"},
		{"300750", "sz300750"},
		{"00700.HK", "hk00700"},
		{"00700", "hk00700"},
		{"700", "hk00700"},
		{"hk00700", "hk00700"},
		{"usAAPL", "gb_aapl"},
		{"gb_AAPL", "gb_aapl"},
		{"430300", "bj430300"},
		{"830001", "bj830001"},
	}
	for _, c := range cases {
		got := GetStockCode(c.in)
		if got != c.want {
			t.Errorf("GetStockCode(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

func TestNormalizeToolStockCodes(t *testing.T) {
	got := normalizeToolStockCodes([]string{"600519", "600519.SH", " sh600519 ", "", "00700.HK"})
	want := []string{"sh600519", "hk00700"}
	if len(got) != len(want) {
		t.Fatalf("normalizeToolStockCodes len = %d, want %d, got %v", len(got), len(want), got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("normalizeToolStockCodes[%d] = %q, want %q", i, got[i], want[i])
		}
	}
}

func TestIsHKOrUSCode(t *testing.T) {
	if !isHKOrUSCode("hk00700") || !isHKOrUSCode("gb_aapl") || !isHKOrUSCode("usAAPL") {
		t.Fatal("expected hk/us/gb_ codes to route as HK/US")
	}
	if isHKOrUSCode("sh600519") || isHKOrUSCode("sz000001") || isHKOrUSCode("bj430300") {
		t.Fatal("A-share codes should not route as HK/US")
	}
}

func TestMarketSentimentZeroTotal(t *testing.T) {
	if got := marketSentiment(0, 0); got != "中性" {
		t.Errorf("marketSentiment(0,0) = %q, want 中性", got)
	}
	if got := marketSentiment(8, 2); got != "极度乐观" {
		t.Errorf("marketSentiment(8,2) = %q, want 极度乐观", got)
	}
}
