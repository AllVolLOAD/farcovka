from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_rate = State()  # Состояние ожидания ввода курса
