from aiogram.fsm.state import State, StatesGroup

class RateStates(StatesGroup):
    waiting_for_rate = State()  # Состояние ожидания ввода курса от админа