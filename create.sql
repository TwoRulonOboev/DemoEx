CREATE DATABASE PartnerProductsDB;
GO

USE PartnerProductsDB;
GO

-- Таблица: Типы продукции
CREATE TABLE [Типы продукции] (
    [Тип продукции] NVARCHAR(50) PRIMARY KEY,
    [Коэффициент типа продукции] FLOAT NOT NULL
);

-- Таблица: Продукция
CREATE TABLE [Продукция] (
    [Артикул] INT PRIMARY KEY,
    [Тип продукции] NVARCHAR(50) NOT NULL REFERENCES [Типы продукции]([Тип продукции]),
    [Наименование продукции] NVARCHAR(255) NOT NULL UNIQUE,
    [Минимальная стоимость для партнера] DECIMAL(10,2) NOT NULL
);

-- Таблица: Партнеры
CREATE TABLE [Партнеры] (
    [Наименование партнера] NVARCHAR(255) PRIMARY KEY,
    [Тип партнера] NVARCHAR(50) NOT NULL,
    [Директор] NVARCHAR(255) NOT NULL,
    [Электронная почта партнера] NVARCHAR(255) NOT NULL,
    [Телефон партнера] NVARCHAR(20) NOT NULL,
    [Юридический адрес партнера] NVARCHAR(255) NOT NULL,
    [ИНН] NVARCHAR(12) NOT NULL,
    [Рейтинг] INT NOT NULL
);

-- Таблица: Запросы партнеров
CREATE TABLE [Запросы партнеров] (
    [ID] INT IDENTITY(1,1) PRIMARY KEY,
    [Продукция] NVARCHAR(255) NOT NULL REFERENCES [Продукция]([Наименование продукции]),
    [Партнер] NVARCHAR(255) NOT NULL REFERENCES [Партнеры]([Наименование партнера]),
    [Количество] INT NOT NULL
);
