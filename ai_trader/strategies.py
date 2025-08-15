from backtesting import Strategy
from backtesting.lib import crossover
from backtesting.test import SMA
import numpy as np


class EMATrend(Strategy):
	n_fast = 10
	n_slow = 30

	def init(self):
		self.ema_fast = self.I(SMA, self.data.Close, self.n_fast)
		self.ema_slow = self.I(SMA, self.data.Close, self.n_slow)

	def next(self):
		if crossover(self.ema_fast, self.ema_slow):
			self.position.close()
			self.buy()
		elif crossover(self.ema_slow, self.ema_fast):
			self.position.close()
			self.sell()


class SMACrossover(Strategy):
	fast = 20
	slow = 50

	def init(self):
		self.sma_fast = self.I(SMA, self.data.Close, self.fast)
		self.sma_slow = self.I(SMA, self.data.Close, self.slow)

	def next(self):
		if crossover(self.sma_fast, self.sma_slow):
			self.position.close()
			self.buy()
		elif crossover(self.sma_slow, self.sma_fast):
			self.position.close()
			self.sell()


class RSIMeanReversion(Strategy):
	period = 14
	oversold = 30
	overbought = 70

	def init(self):
		self.delta = self.data.Close.diff()
		gain = self.I(lambda x: np.where(x > 0, x, 0), self.delta)
		loss = self.I(lambda x: np.where(x < 0, -x, 0), self.delta)
		rsi = self.I(self._calc_rsi, gain, loss)
		self.rsi = rsi

	@staticmethod
	def _calc_rsi(gain, loss, period: int = 14):
		avg_gain = SMA(gain, period)
		avg_loss = SMA(loss, period)
		rs = np.divide(avg_gain, np.where(avg_loss == 0, 1e-9, avg_loss))
		return 100 - (100 / (1 + rs))

	def next(self):
		if self.rsi[-1] < self.oversold:
			self.buy()
		elif self.rsi[-1] > self.overbought:
			self.sell()


class DonchianBreakout(Strategy):
	window = 20

	def init(self):
		self.high_roll = self.I(lambda x: np.maximum.accumulate(x), self.data.High)
		self.low_roll = self.I(lambda x: np.minimum.accumulate(x), self.data.Low)

	def next(self):
		if self.data.Close[-1] >= max(self.data.Close[-self.window:]):
			self.buy()
		elif self.data.Close[-1] <= min(self.data.Close[-self.window:]):
			self.sell()


class MACDTrend(Strategy):
	fast = 12
	slow = 26
	signal = 9

	def init(self):
		self.ema_fast = self.I(SMA, self.data.Close, self.fast)
		self.ema_slow = self.I(SMA, self.data.Close, self.slow)
		self.macd = self.I(lambda f, s: f - s, self.ema_fast, self.ema_slow)
		self.signal_line = self.I(SMA, self.macd, self.signal)

	def next(self):
		if crossover(self.macd, self.signal_line):
			self.buy()
		elif crossover(self.signal_line, self.macd):
			self.sell()


ALL_STRATEGIES = {
	"ema_trend": EMATrend,
	"sma_cross": SMACrossover,
	"rsi_mean": RSIMeanReversion,
	"donchian": DonchianBreakout,
	"macd_trend": MACDTrend,
}