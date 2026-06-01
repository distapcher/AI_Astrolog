from aiogram.fsm.state import State, StatesGroup


class NatalChartStates(StatesGroup):
    name = State()
    birth_date = State()
    birth_time = State()
    birth_place = State()
    birth_nation = State()
