"""Перечисления доменной области приложения."""

from __future__ import annotations

from enum import Enum


class ProductionCountry(str, Enum):
    """Список стран производства для фильтрации в Swagger через выпадающий список."""

    RUSSIA = "Россия"
    BELARUS = "Беларусь"
    KAZAKHSTAN = "Казахстан"
    ARMENIA = "Армения"
    KYRGYZSTAN = "Киргизия"
    UZBEKISTAN = "Узбекистан"
    TAJIKISTAN = "Таджикистан"
    AZERBAIJAN = "Азербайджан"
    GEORGIA = "Грузия"
    UKRAINE = "Украина"
    CHINA = "Китай"
    TURKEY = "Турция"
    ITALY = "Италия"
    FRANCE = "Франция"
    GERMANY = "Германия"
    SPAIN = "Испания"
    PORTUGAL = "Португалия"
    POLAND = "Польша"
    ROMANIA = "Румыния"
    BULGARIA = "Болгария"
    GREECE = "Греция"
    HUNGARY = "Венгрия"
    CZECH_REPUBLIC = "Чехия"
    SLOVAKIA = "Словакия"
    SLOVENIA = "Словения"
    CROATIA = "Хорватия"
    SERBIA = "Сербия"
    BOSNIA_AND_HERZEGOVINA = "Босния и Герцеговина"
    NORTH_MACEDONIA = "Северная Македония"
    MOLDOVA = "Молдова"
    LITHUANIA = "Литва"
    LATVIA = "Латвия"
    ESTONIA = "Эстония"
    FINLAND = "Финляндия"
    SWEDEN = "Швеция"
    NORWAY = "Норвегия"
    DENMARK = "Дания"
    NETHERLANDS = "Нидерланды"
    BELGIUM = "Бельгия"
    SWITZERLAND = "Швейцария"
    AUSTRIA = "Австрия"
    UNITED_KINGDOM = "Великобритания"
    IRELAND = "Ирландия"
    USA = "США"
    CANADA = "Канада"
    MEXICO = "Мексика"
    BRAZIL = "Бразилия"
    ARGENTINA = "Аргентина"
    CHILE = "Чили"
    PERU = "Перу"
    COLOMBIA = "Колумбия"
    INDIA = "Индия"
    PAKISTAN = "Пакистан"
    BANGLADESH = "Бангладеш"
    VIETNAM = "Вьетнам"
    THAILAND = "Таиланд"
    INDONESIA = "Индонезия"
    MALAYSIA = "Малайзия"
    SINGAPORE = "Сингапур"
    SOUTH_KOREA = "Южная Корея"
    NORTH_KOREA = "Северная Корея"
    JAPAN = "Япония"
    TAIWAN = "Тайвань"
    HONG_KONG = "Гонконг"
    MONGOLIA = "Монголия"
    NEPAL = "Непал"
    SRI_LANKA = "Шри-Ланка"
    UNITED_ARAB_EMIRATES = "ОАЭ"
    SAUDI_ARABIA = "Саудовская Аравия"
    ISRAEL = "Израиль"
    JORDAN = "Иордания"
    EGYPT = "Египет"
    MOROCCO = "Марокко"
    TUNISIA = "Тунис"
    ALGERIA = "Алжир"
    SOUTH_AFRICA = "ЮАР"
    AUSTRALIA = "Австралия"
    NEW_ZEALAND = "Новая Зеландия"


COUNTRY_FILTER_ALIASES: dict[ProductionCountry, tuple[str, ...]] = {
    ProductionCountry.RUSSIA: ("россия", "российская федерация", "рф"),
    ProductionCountry.BELARUS: ("беларусь", "республика беларусь"),
    ProductionCountry.KAZAKHSTAN: ("казахстан", "республика казахстан"),
    ProductionCountry.KYRGYZSTAN: ("киргизия", "кыргызстан", "киргизская республика"),
    ProductionCountry.USA: ("сша", "соединенные штаты", "соединенные штаты америки", "usa"),
    ProductionCountry.UNITED_KINGDOM: ("великобритания", "британия", "соединенное королевство", "uk"),
    ProductionCountry.SOUTH_KOREA: ("южная корея", "корея", "республика корея"),
    ProductionCountry.NORTH_KOREA: ("северная корея", "кндр"),
    ProductionCountry.UNITED_ARAB_EMIRATES: ("оаэ", "объединенные арабские эмираты"),
}
