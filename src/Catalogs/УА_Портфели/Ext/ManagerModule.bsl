﻿#Область ПрограммныйИнтерфейс

Функция ПортфельПоУмолчанию() Экспорт
	
	Результат = ПустаяСсылка();
	
	Выборка = Выбрать();
	
	Если Выборка.Следующий() Тогда
		Объект = Выборка.ПолучитьОбъект();
		Результат = Объект.Ссылка;
	КонецЕсли;
	
	Возврат Результат;	
	
КонецФункции

#КонецОбласти