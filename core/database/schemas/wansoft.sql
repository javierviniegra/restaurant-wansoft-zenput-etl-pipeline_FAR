-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 28-05-2026 a las 20:55:09
-- Versión del servidor: 10.4.28-MariaDB
-- Versión de PHP: 8.2.4

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `wansoft`
--
CREATE DATABASE IF NOT EXISTS `wansoft` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE `wansoft`;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `costeomensual`
--

CREATE TABLE `costeomensual` (
  `id` int(11) NOT NULL,
  `subsidiary_id` int(11) DEFAULT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `CostoTotal` decimal(10,2) DEFAULT NULL,
  `CostoDeProductosVendidos` decimal(10,2) DEFAULT NULL,
  `CostoIdealDeProductosPendientesDeRebaja` decimal(10,2) DEFAULT NULL,
  `CostoDeCortesías` decimal(10,2) DEFAULT NULL,
  `CostoDeCancelaciones` decimal(10,2) DEFAULT NULL,
  `CostoDeMerma` decimal(10,2) DEFAULT NULL,
  `CostoDeDesperdicio` decimal(10,2) DEFAULT NULL,
  `CostoDeRobo` decimal(10,2) DEFAULT NULL,
  `CostoDeConsumo` decimal(10,2) DEFAULT NULL,
  `AjustePorSobrantes` decimal(10,2) DEFAULT NULL,
  `UtilidadMarginal` decimal(10,2) DEFAULT NULL,
  `mes_ano` varchar(7) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `costeomensual_semanapyq`
--

CREATE TABLE `costeomensual_semanapyq` (
  `id` int(11) NOT NULL,
  `subsidiary_id` int(11) DEFAULT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `CostoTotal` decimal(10,2) DEFAULT NULL,
  `CostoDeProductosVendidos` decimal(10,2) DEFAULT NULL,
  `CostoIdealDeProductosPendientesDeRebaja` decimal(10,2) DEFAULT NULL,
  `CostoDeCortesías` decimal(10,2) DEFAULT NULL,
  `CostoDeCancelaciones` decimal(10,2) DEFAULT NULL,
  `CostoDeMerma` decimal(10,2) DEFAULT NULL,
  `CostoDeDesperdicio` decimal(10,2) DEFAULT NULL,
  `CostoDeRobo` decimal(10,2) DEFAULT NULL,
  `CostoDeConsumo` decimal(10,2) DEFAULT NULL,
  `AjustePorSobrantes` decimal(10,2) DEFAULT NULL,
  `UtilidadMarginal` decimal(10,2) DEFAULT NULL,
  `mes_ano` varchar(7) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getallordenesbyday_detalleventa`
--

CREATE TABLE `getallordenesbyday_detalleventa` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Movimiento_Id` varchar(255) DEFAULT NULL,
  `DetalleVenta_Id` varchar(255) DEFAULT NULL,
  `Descripcion` varchar(255) DEFAULT NULL,
  `Cantidad` varchar(255) DEFAULT NULL,
  `PrecioUnitario` varchar(255) DEFAULT NULL,
  `Descuento` varchar(255) DEFAULT NULL,
  `Subtotal` varchar(255) DEFAULT NULL,
  `IVA` varchar(255) DEFAULT NULL,
  `IEPS` varchar(255) DEFAULT NULL,
  `Total` varchar(255) DEFAULT NULL,
  `Modificador` varchar(255) DEFAULT NULL,
  `Hora` varchar(255) DEFAULT NULL,
  `Costo` varchar(255) DEFAULT NULL,
  `TipoGrupo` varchar(255) DEFAULT NULL,
  `CodigoTipoGrupo` varchar(255) DEFAULT NULL,
  `CuentaContableTipoGrupo` varchar(255) DEFAULT NULL,
  `Grupo` varchar(255) DEFAULT NULL,
  `CodigoGrupo` varchar(255) DEFAULT NULL,
  `CuentaContableGrupo` varchar(255) DEFAULT NULL,
  `CodigoPlatillo` varchar(255) DEFAULT NULL,
  `CuentaContablePlatillo` varchar(255) DEFAULT NULL,
  `Platillo` varchar(255) DEFAULT NULL,
  `ConIVA` varchar(255) DEFAULT NULL,
  `ComandaId` varchar(255) DEFAULT NULL,
  `TipoPlatilloId` varchar(255) DEFAULT NULL,
  `TipoPromocionId` varchar(255) DEFAULT NULL,
  `Cortesia` varchar(255) DEFAULT NULL,
  `DetallesVenta_Id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getallordenesbyday_modificador`
--

CREATE TABLE `getallordenesbyday_modificador` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Movimiento_Id` varchar(255) DEFAULT NULL,
  `Descripcion` varchar(255) DEFAULT NULL,
  `Cantidad` varchar(255) DEFAULT NULL,
  `PrecioUnitario` varchar(255) DEFAULT NULL,
  `Descuento` varchar(255) DEFAULT NULL,
  `Subtotal` varchar(255) DEFAULT NULL,
  `IVA` varchar(255) DEFAULT NULL,
  `IEPS` varchar(255) DEFAULT NULL,
  `Total` varchar(255) DEFAULT NULL,
  `Modificador` varchar(255) DEFAULT NULL,
  `Hora` varchar(255) DEFAULT NULL,
  `Costo` varchar(255) DEFAULT NULL,
  `TipoGrupo` varchar(255) DEFAULT NULL,
  `CodigoTipoGrupo` varchar(255) DEFAULT NULL,
  `CuentaContableTipoGrupo` varchar(255) DEFAULT NULL,
  `Grupo` varchar(255) DEFAULT NULL,
  `CodigoGrupo` varchar(255) DEFAULT NULL,
  `CuentaContableGrupo` varchar(255) DEFAULT NULL,
  `CodigoPlatillo` varchar(255) DEFAULT NULL,
  `CuentaContablePlatillo` varchar(255) DEFAULT NULL,
  `Platillo` varchar(255) DEFAULT NULL,
  `ConIVA` varchar(255) DEFAULT NULL,
  `ComandaId` varchar(255) DEFAULT NULL,
  `TipoPlatilloId` varchar(255) DEFAULT NULL,
  `TipoPromocionId` varchar(255) DEFAULT NULL,
  `Modificadores_Id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getallordenesbyday_new_detalleventa`
--

CREATE TABLE `getallordenesbyday_new_detalleventa` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Movimiento_Id` varchar(255) DEFAULT NULL,
  `DetalleVenta_Id` varchar(255) DEFAULT NULL,
  `Descripcion` varchar(255) DEFAULT NULL,
  `Cantidad` varchar(255) DEFAULT NULL,
  `PrecioUnitario` varchar(255) DEFAULT NULL,
  `Descuento` varchar(255) DEFAULT NULL,
  `Subtotal` varchar(255) DEFAULT NULL,
  `IVA` varchar(255) DEFAULT NULL,
  `IEPS` varchar(255) DEFAULT NULL,
  `Total` varchar(255) DEFAULT NULL,
  `Modificador` varchar(255) DEFAULT NULL,
  `Hora` varchar(255) DEFAULT NULL,
  `Costo` varchar(255) DEFAULT NULL,
  `TipoGrupo` varchar(255) DEFAULT NULL,
  `CodigoTipoGrupo` varchar(255) DEFAULT NULL,
  `CuentaContableTipoGrupo` varchar(255) DEFAULT NULL,
  `Grupo` varchar(255) DEFAULT NULL,
  `CodigoGrupo` varchar(255) DEFAULT NULL,
  `CuentaContableGrupo` varchar(255) DEFAULT NULL,
  `CodigoPlatillo` varchar(255) DEFAULT NULL,
  `CuentaContablePlatillo` varchar(255) DEFAULT NULL,
  `Platillo` varchar(255) DEFAULT NULL,
  `ConIVA` varchar(255) DEFAULT NULL,
  `ComandaId` varchar(255) DEFAULT NULL,
  `TipoPlatilloId` varchar(255) DEFAULT NULL,
  `TipoPromocionId` varchar(255) DEFAULT NULL,
  `Cortesia` varchar(255) DEFAULT NULL,
  `DetallesVenta_Id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getallordenesbyday_new_modificador`
--

CREATE TABLE `getallordenesbyday_new_modificador` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Movimiento_Id` varchar(255) DEFAULT NULL,
  `Descripcion` varchar(255) DEFAULT NULL,
  `Cantidad` varchar(255) DEFAULT NULL,
  `PrecioUnitario` varchar(255) DEFAULT NULL,
  `Descuento` varchar(255) DEFAULT NULL,
  `Subtotal` varchar(255) DEFAULT NULL,
  `IVA` varchar(255) DEFAULT NULL,
  `IEPS` varchar(255) DEFAULT NULL,
  `Total` varchar(255) DEFAULT NULL,
  `Modificador` varchar(255) DEFAULT NULL,
  `Hora` varchar(255) DEFAULT NULL,
  `Costo` varchar(255) DEFAULT NULL,
  `TipoGrupo` varchar(255) DEFAULT NULL,
  `CodigoTipoGrupo` varchar(255) DEFAULT NULL,
  `CuentaContableTipoGrupo` varchar(255) DEFAULT NULL,
  `Grupo` varchar(255) DEFAULT NULL,
  `CodigoGrupo` varchar(255) DEFAULT NULL,
  `CuentaContableGrupo` varchar(255) DEFAULT NULL,
  `CodigoPlatillo` varchar(255) DEFAULT NULL,
  `CuentaContablePlatillo` varchar(255) DEFAULT NULL,
  `Platillo` varchar(255) DEFAULT NULL,
  `ConIVA` varchar(255) DEFAULT NULL,
  `ComandaId` varchar(255) DEFAULT NULL,
  `TipoPlatilloId` varchar(255) DEFAULT NULL,
  `TipoPromocionId` varchar(255) DEFAULT NULL,
  `Modificadores_Id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getallordenesbyday_new_pago`
--

CREATE TABLE `getallordenesbyday_new_pago` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Movimiento_Id` varchar(255) DEFAULT NULL,
  `Fecha` varchar(255) DEFAULT NULL,
  `IdMetodoDePago` varchar(255) DEFAULT NULL,
  `MetodoDePago` varchar(255) DEFAULT NULL,
  `CodigoMetodoDePago` varchar(255) DEFAULT NULL,
  `ClaveSATMetodoDePago` varchar(255) DEFAULT NULL,
  `CuentaContableMetodoDePago` varchar(255) DEFAULT NULL,
  `Terminal` varchar(255) DEFAULT NULL,
  `Total` varchar(255) DEFAULT NULL,
  `Propina` varchar(255) DEFAULT NULL,
  `Equivalencia` varchar(255) DEFAULT NULL,
  `Moneda` varchar(255) DEFAULT NULL,
  `MontoRecibidoEnMoneda` varchar(255) DEFAULT NULL,
  `PagoAnticipadoId` varchar(255) DEFAULT NULL,
  `Pagos_Id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getallordenesbyday_new_pagos`
--

CREATE TABLE `getallordenesbyday_new_pagos` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Pagos_Id` varchar(255) DEFAULT NULL,
  `Venta_Id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getallordenesbyday_new_venta`
--

CREATE TABLE `getallordenesbyday_new_venta` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Venta_Id` varchar(255) DEFAULT NULL,
  `Movimento` varchar(255) DEFAULT NULL,
  `Orden` varchar(255) DEFAULT NULL,
  `Mesa` varchar(255) DEFAULT NULL,
  `Fecha` varchar(255) DEFAULT NULL,
  `Mesero` varchar(255) DEFAULT NULL,
  `Subtotal` varchar(255) DEFAULT NULL,
  `IVA` varchar(255) DEFAULT NULL,
  `IEPS` varchar(255) DEFAULT NULL,
  `Total` varchar(255) DEFAULT NULL,
  `Terminal` varchar(255) DEFAULT NULL,
  `Personas` varchar(255) DEFAULT NULL,
  `Descuento` varchar(255) DEFAULT NULL,
  `Impuesto` varchar(255) DEFAULT NULL,
  `MontoDescontado` varchar(255) DEFAULT NULL,
  `TipoOrden` varchar(255) DEFAULT NULL,
  `HoraApertura` varchar(255) DEFAULT NULL,
  `HoraCierre` varchar(255) DEFAULT NULL,
  `Moneda` varchar(255) DEFAULT NULL,
  `CodigoCliente` varchar(255) DEFAULT NULL,
  `Estatus` varchar(255) DEFAULT NULL,
  `Ventas_Id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getallordenesbyday_venta`
--

CREATE TABLE `getallordenesbyday_venta` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Venta_Id` varchar(255) DEFAULT NULL,
  `Movimento` varchar(255) DEFAULT NULL,
  `Orden` varchar(255) DEFAULT NULL,
  `Mesa` varchar(255) DEFAULT NULL,
  `Fecha` varchar(255) DEFAULT NULL,
  `Mesero` varchar(255) DEFAULT NULL,
  `Subtotal` varchar(255) DEFAULT NULL,
  `IVA` varchar(255) DEFAULT NULL,
  `IEPS` varchar(255) DEFAULT NULL,
  `Total` varchar(255) DEFAULT NULL,
  `Terminal` varchar(255) DEFAULT NULL,
  `Personas` varchar(255) DEFAULT NULL,
  `Descuento` varchar(255) DEFAULT NULL,
  `Impuesto` varchar(255) DEFAULT NULL,
  `MontoDescontado` varchar(255) DEFAULT NULL,
  `TipoOrden` varchar(255) DEFAULT NULL,
  `HoraApertura` varchar(255) DEFAULT NULL,
  `HoraCierre` varchar(255) DEFAULT NULL,
  `Moneda` varchar(255) DEFAULT NULL,
  `CodigoCliente` varchar(255) DEFAULT NULL,
  `Estatus` varchar(255) DEFAULT NULL,
  `Ventas_Id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getcostreport`
--

CREATE TABLE `getcostreport` (
  `id` int(11) NOT NULL,
  `subsidiary_id` int(11) DEFAULT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `CostoTotal` decimal(10,2) DEFAULT NULL,
  `CostoDeProductosVendidos` decimal(10,2) DEFAULT NULL,
  `CostoIdealDeProductosPendientesDeRebaja` decimal(10,2) DEFAULT NULL,
  `CostoDeCortesías` decimal(10,2) DEFAULT NULL,
  `CostoDeCancelaciones` decimal(10,2) DEFAULT NULL,
  `CostoDeMerma` decimal(10,2) DEFAULT NULL,
  `CostoDeDesperdicio` decimal(10,2) DEFAULT NULL,
  `CostoDeRobo` decimal(10,2) DEFAULT NULL,
  `CostoDeConsumo` decimal(10,2) DEFAULT NULL,
  `AjustePorSobrantes` decimal(10,2) DEFAULT NULL,
  `UtilidadMarginal` decimal(10,2) DEFAULT NULL,
  `mes_ano` varchar(7) DEFAULT NULL,
  `fecha` varchar(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getexpensesbyinputdate`
--

CREATE TABLE `getexpensesbyinputdate` (
  `id` int(11) NOT NULL,
  `IdDocumento` varchar(255) DEFAULT NULL,
  `Folio` varchar(255) DEFAULT NULL,
  `RFCProveedor` varchar(255) DEFAULT NULL,
  `NombreProveedor` varchar(255) DEFAULT NULL,
  `ClaveProveedor` varchar(255) DEFAULT NULL,
  `CuentaContableProveedor` varchar(255) DEFAULT NULL,
  `Subtotal` varchar(255) DEFAULT NULL,
  `IVA` varchar(255) DEFAULT NULL,
  `IEPS` varchar(255) DEFAULT NULL,
  `Total` varchar(255) DEFAULT NULL,
  `FechaDeExpedicion` varchar(255) DEFAULT NULL,
  `FechaDeExpiracion` varchar(255) DEFAULT NULL,
  `TerminosDePago` varchar(255) DEFAULT NULL,
  `Cuenta` varchar(255) DEFAULT NULL,
  `Subcuenta` varchar(255) DEFAULT NULL,
  `Estatus` varchar(255) DEFAULT NULL,
  `TotalDeudor` varchar(255) DEFAULT NULL,
  `TipoDeEgreso` varchar(255) DEFAULT NULL,
  `UUID` varchar(255) DEFAULT NULL,
  `IdOrdenCompra` varchar(255) DEFAULT NULL,
  `FolioOrdenCompra` varchar(255) DEFAULT NULL,
  `FechaDeRegistro` varchar(255) DEFAULT NULL,
  `DiasCredito` varchar(255) DEFAULT NULL,
  `ColoniaProveedor` varchar(255) DEFAULT NULL,
  `CiudadProveedor` varchar(255) DEFAULT NULL,
  `CPProveedor` varchar(255) DEFAULT NULL,
  `TelefonoProveedor` varchar(255) DEFAULT NULL,
  `CorreoProveedor` varchar(255) DEFAULT NULL,
  `CalleProveedor` varchar(255) DEFAULT NULL,
  `NumeroIntProveedor` varchar(255) DEFAULT NULL,
  `NumeroExtProveedor` varchar(255) DEFAULT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `current_fecha` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getexpenses_factura`
--

CREATE TABLE `getexpenses_factura` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Factura_Id` varchar(255) DEFAULT NULL,
  `IdDocumento` varchar(255) DEFAULT NULL,
  `Folio` varchar(255) DEFAULT NULL,
  `RFCProveedor` varchar(255) DEFAULT NULL,
  `NombreProveedor` varchar(255) DEFAULT NULL,
  `ClaveProveedor` varchar(255) DEFAULT NULL,
  `CuentaContableProveedor` varchar(255) DEFAULT NULL,
  `Subtotal` varchar(255) DEFAULT NULL,
  `IVA` varchar(255) DEFAULT NULL,
  `IEPS` varchar(255) DEFAULT NULL,
  `Total` varchar(255) DEFAULT NULL,
  `FechaDeExpedicion` varchar(255) DEFAULT NULL,
  `FechaDeExpiracion` varchar(255) DEFAULT NULL,
  `TerminosDePago` varchar(255) DEFAULT NULL,
  `Cuenta` varchar(255) DEFAULT NULL,
  `Subcuenta` varchar(255) DEFAULT NULL,
  `Estatus` varchar(255) DEFAULT NULL,
  `TotalDeudor` varchar(255) DEFAULT NULL,
  `TipoDeEgreso` varchar(255) DEFAULT NULL,
  `UUID` varchar(255) DEFAULT NULL,
  `IdOrdenCompra` varchar(255) DEFAULT NULL,
  `FolioOrdenCompra` varchar(255) DEFAULT NULL,
  `FechaDeRegistro` varchar(255) DEFAULT NULL,
  `DiasCredito` varchar(255) DEFAULT NULL,
  `ColoniaProveedor` varchar(255) DEFAULT NULL,
  `CiudadProveedor` varchar(255) DEFAULT NULL,
  `CPProveedor` varchar(255) DEFAULT NULL,
  `TelefonoProveedor` varchar(255) DEFAULT NULL,
  `CorreoProveedor` varchar(255) DEFAULT NULL,
  `CalleProveedor` varchar(255) DEFAULT NULL,
  `NumeroIntProveedor` varchar(255) DEFAULT NULL,
  `NumeroExtProveedor` varchar(255) DEFAULT NULL,
  `Discount` varchar(255) DEFAULT NULL,
  `Retentions` varchar(255) DEFAULT NULL,
  `Egresos_Id` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getglobalcashclosing`
--

CREATE TABLE `getglobalcashclosing` (
  `id` int(11) NOT NULL,
  `subsidiary_id` int(11) DEFAULT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `fecha_corte` datetime DEFAULT NULL,
  `usuario` varchar(255) DEFAULT NULL,
  `subtotal` decimal(10,2) DEFAULT NULL,
  `iva` decimal(10,2) DEFAULT NULL,
  `ieps` decimal(10,2) DEFAULT NULL,
  `total_ventas` decimal(10,2) DEFAULT NULL,
  `efectivo_por_ventas` decimal(10,2) DEFAULT NULL,
  `efectivo_por_propina` decimal(10,2) DEFAULT NULL,
  `fondo_de_caja` decimal(10,2) DEFAULT NULL,
  `efectivo_real` decimal(10,2) DEFAULT NULL,
  `no_ordenes` int(11) DEFAULT NULL,
  `no_platillos` int(11) DEFAULT NULL,
  `total_personas` int(11) DEFAULT NULL,
  `promedio_platillos_orden` decimal(10,2) DEFAULT NULL,
  `promedio_por_orden` decimal(10,2) DEFAULT NULL,
  `promedio_por_persona` decimal(10,2) DEFAULT NULL,
  `total_ordenes_para_llevar` int(11) DEFAULT NULL,
  `total_mesas_atendidas` int(11) DEFAULT NULL,
  `total_ordenes_a_domicilio` int(11) DEFAULT NULL,
  `total_ordenes_recoger` int(11) DEFAULT NULL,
  `no_cortesias_en_cuentas` int(11) DEFAULT NULL,
  `cortesias_en_cuentas` decimal(10,2) DEFAULT NULL,
  `no_cortesias_en_platillos` int(11) DEFAULT NULL,
  `cortesias_en_platillos` decimal(10,2) DEFAULT NULL,
  `no_cancelaciones_en_cuentas` int(11) DEFAULT NULL,
  `cancelaciones_en_cuentas` decimal(10,2) DEFAULT NULL,
  `no_cancelaciones_en_platillos` int(11) DEFAULT NULL,
  `cancelaciones_en_platillos` decimal(10,2) DEFAULT NULL,
  `no_descuentos_en_cuentas` int(11) DEFAULT NULL,
  `descuentos_en_cuentas` decimal(10,2) DEFAULT NULL,
  `no_descuentos_en_platillos` int(11) DEFAULT NULL,
  `descuentos_en_platillos` decimal(10,2) DEFAULT NULL,
  `no_anulaciones_en_cuentas` int(11) DEFAULT NULL,
  `anulaciones_en_cuentas` decimal(10,2) DEFAULT NULL,
  `no_anulaciones_en_platillos` int(11) DEFAULT NULL,
  `anulaciones_en_platillos` decimal(10,2) DEFAULT NULL,
  `no_dxu_platillos` int(11) DEFAULT NULL,
  `dxu_platillos` decimal(10,2) DEFAULT NULL,
  `no_descuentos_megapuntos` int(11) DEFAULT NULL,
  `descuentos_megapuntos` decimal(10,2) DEFAULT NULL,
  `no_promociones` int(11) DEFAULT NULL,
  `promociones` decimal(10,2) DEFAULT NULL,
  `no_cupones` int(11) DEFAULT NULL,
  `cupones` decimal(10,2) DEFAULT NULL,
  `mes_ano` varchar(7) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getinputinventory_entrada`
--

CREATE TABLE `getinputinventory_entrada` (
  `id` int(11) NOT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `IdEntrada` varchar(50) DEFAULT NULL,
  `ClaveAlmacen` varchar(50) DEFAULT NULL,
  `Almacen` varchar(255) DEFAULT NULL,
  `IdAlmacen` int(11) DEFAULT NULL,
  `CuentaContableAlmacen` varchar(255) DEFAULT NULL,
  `CodigoDepartamento` varchar(255) DEFAULT NULL,
  `Departamento` varchar(255) DEFAULT NULL,
  `CuentaContableDepartamento` varchar(255) DEFAULT NULL,
  `IdProducto` int(11) DEFAULT NULL,
  `CodigoProducto` varchar(50) DEFAULT NULL,
  `NombreProducto` varchar(255) DEFAULT NULL,
  `CodigoUnidadDeMedida` varchar(50) DEFAULT NULL,
  `IdUnidadDeMedida` int(11) DEFAULT NULL,
  `UnidadDeMedida` varchar(50) DEFAULT NULL,
  `TipoEntrada` varchar(50) DEFAULT NULL,
  `Cantidad` decimal(15,10) DEFAULT NULL,
  `CostoUnitario` decimal(15,4) DEFAULT NULL,
  `ProductoConIVA` tinyint(1) DEFAULT NULL,
  `Caducidad` date DEFAULT NULL,
  `FechaEntrada` datetime DEFAULT NULL,
  `Factura` varchar(50) DEFAULT NULL,
  `FechaFactura` date DEFAULT NULL,
  `RFCProveedor` varchar(50) DEFAULT NULL,
  `ClaveProveedor` varchar(50) DEFAULT NULL,
  `NombreProveedor` varchar(255) DEFAULT NULL,
  `IdTransferencia` int(11) DEFAULT NULL,
  `FolioTransferencia` varchar(50) DEFAULT NULL,
  `IdOrdenCompra` int(11) DEFAULT NULL,
  `FolioOrdenCompra` varchar(50) DEFAULT NULL,
  `RFCProveedorOrdenCompra` varchar(50) DEFAULT NULL,
  `ProveedorOrdenCompra` varchar(255) DEFAULT NULL,
  `IdDocumento` int(11) DEFAULT NULL,
  `IdUsuario` int(11) DEFAULT NULL,
  `NombreUsuario` varchar(255) DEFAULT NULL,
  `FechaReal` date DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getinventorybydepartment`
--

CREATE TABLE `getinventorybydepartment` (
  `CodigoProducto` varchar(255) DEFAULT NULL,
  `Producto` varchar(255) DEFAULT NULL,
  `UnidadDeMedida` varchar(255) DEFAULT NULL,
  `Existencia` varchar(255) DEFAULT NULL,
  `CostoPromedio` varchar(255) DEFAULT NULL,
  `Monto` varchar(255) DEFAULT NULL,
  `MontoTotal` varchar(255) DEFAULT NULL,
  `Departamento` varchar(255) DEFAULT NULL,
  `ClaveDepartamento` varchar(255) DEFAULT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `current_fecha` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getoutgoinginventory_salida`
--

CREATE TABLE `getoutgoinginventory_salida` (
  `id` int(11) NOT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `IdSalida` varchar(50) DEFAULT NULL,
  `IdEntrada` varchar(50) DEFAULT NULL,
  `IdAlmacen` int(11) DEFAULT NULL,
  `Almacen` varchar(255) DEFAULT NULL,
  `CuentaContableAlmacen` varchar(255) DEFAULT NULL,
  `CuentaContableDepartamento` varchar(255) DEFAULT NULL,
  `Departamento` varchar(255) DEFAULT NULL,
  `IdProducto` int(11) DEFAULT NULL,
  `CodigoProducto` varchar(50) DEFAULT NULL,
  `NombreProducto` varchar(255) DEFAULT NULL,
  `CodigoUnidadDeMedida` varchar(50) DEFAULT NULL,
  `IdUnidadDeMedida` int(11) DEFAULT NULL,
  `UnidadDeMedida` varchar(50) DEFAULT NULL,
  `TipoSalida` varchar(50) DEFAULT NULL,
  `Cantidad` decimal(15,10) DEFAULT NULL,
  `CostoUnitario` decimal(15,4) DEFAULT NULL,
  `Caducidad` date DEFAULT NULL,
  `FechaSalida` datetime DEFAULT NULL,
  `IdTransferencia` varchar(50) DEFAULT NULL,
  `FolioTransferencia` varchar(50) DEFAULT NULL,
  `Orden` varchar(50) DEFAULT NULL,
  `Fecha` date DEFAULT NULL,
  `IdDetalleVenta` varchar(50) DEFAULT NULL,
  `IdUsuario` varchar(50) DEFAULT NULL,
  `NombreUsuario` varchar(255) DEFAULT NULL,
  `FechaReal` date DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getpendingpurchaseorders`
--

CREATE TABLE `getpendingpurchaseorders` (
  `id` int(11) NOT NULL,
  `orden_id` varchar(50) NOT NULL,
  `estatus_id` int(11) DEFAULT NULL,
  `estatus` varchar(50) DEFAULT NULL,
  `es_sugerida` tinyint(1) DEFAULT NULL,
  `clave_sucursal_origen` varchar(50) DEFAULT NULL,
  `referencia` varchar(100) DEFAULT NULL,
  `clave_almacen` varchar(50) DEFAULT NULL,
  `almacen` varchar(255) DEFAULT NULL,
  `proveedor` varchar(255) DEFAULT NULL,
  `clave_proveedor` varchar(50) DEFAULT NULL,
  `rfc_proveedor` varchar(20) DEFAULT NULL,
  `fecha_creacion` datetime DEFAULT NULL,
  `usuario_emisor` varchar(255) DEFAULT NULL,
  `total` decimal(15,6) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `subsidiary_name` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getpendingpurchaseorders_details`
--

CREATE TABLE `getpendingpurchaseorders_details` (
  `id` int(11) NOT NULL,
  `orden_id` int(11) DEFAULT NULL,
  `codigo_producto` varchar(100) DEFAULT NULL,
  `producto` varchar(255) DEFAULT NULL,
  `cantidad` decimal(15,10) DEFAULT NULL,
  `unidad_medida` varchar(50) DEFAULT NULL,
  `codigo_unidad_medida` varchar(10) DEFAULT NULL,
  `presentacion` varchar(100) DEFAULT NULL,
  `contenido_presentacion` decimal(15,10) DEFAULT NULL,
  `precio_unitario_sugerido_um` decimal(15,4) DEFAULT NULL,
  `precio_unitario_sugerido_presentacion` decimal(15,4) DEFAULT NULL,
  `total_sugerido` decimal(15,4) DEFAULT NULL,
  `stock_minimo` decimal(15,10) DEFAULT NULL,
  `stock_maximo` decimal(15,10) DEFAULT NULL,
  `existencia_actual` int(11) DEFAULT NULL,
  `en_proceso` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `getstockinventory_inventario`
--

CREATE TABLE `getstockinventory_inventario` (
  `id` int(11) NOT NULL,
  `Sucursal` varchar(255) DEFAULT NULL,
  `Fecha` varchar(255) DEFAULT NULL,
  `IdProducto` varchar(255) DEFAULT NULL,
  `CodigoProducto` varchar(255) DEFAULT NULL,
  `Producto` varchar(255) DEFAULT NULL,
  `IdDepartamento` varchar(255) DEFAULT NULL,
  `CodigoDepartamento` varchar(255) DEFAULT NULL,
  `Departamento` varchar(255) DEFAULT NULL,
  `IdUnidadDeMedida` varchar(255) DEFAULT NULL,
  `UnidadDeMedida` varchar(255) DEFAULT NULL,
  `Disponibilidad` varchar(255) DEFAULT NULL,
  `Balance` varchar(255) DEFAULT NULL,
  `Critico` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `gettablajeriareport`
--

CREATE TABLE `gettablajeriareport` (
  `id` int(11) NOT NULL,
  `subsidiary_id` int(11) DEFAULT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `InputDate` date DEFAULT NULL,
  `UserName` varchar(255) DEFAULT NULL,
  `QuantityOfBaseProduct` decimal(15,10) DEFAULT NULL,
  `ProductBase` varchar(255) DEFAULT NULL,
  `ProductBaseCost` decimal(15,4) DEFAULT NULL,
  `UnitOfMeasureOfBaseProduct` varchar(50) DEFAULT NULL,
  `QuantityDecrease` decimal(15,10) DEFAULT NULL,
  `Warehouse` varchar(255) DEFAULT NULL,
  `QuantityOfGeneratedProduct` decimal(15,10) DEFAULT NULL,
  `GeneratedProduct` varchar(255) DEFAULT NULL,
  `UnitCostOfGeneratedProduct` decimal(15,10) DEFAULT NULL,
  `totalCostOfGeneratedProduct` decimal(15,10) DEFAULT NULL,
  `RegistrationDate` date DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `gettotalcostbydate`
--

CREATE TABLE `gettotalcostbydate` (
  `id` int(11) NOT NULL,
  `subsidiary_id` int(11) DEFAULT NULL,
  `subsidiary_name` varchar(255) DEFAULT NULL,
  `CostoTotalVenta` decimal(10,2) DEFAULT NULL,
  `mes_ano` varchar(7) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `product_catalog_mapping`
--

CREATE TABLE product_catalog_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_system VARCHAR(20) NOT NULL,
    wansoft_code VARCHAR(50) NULL,
    odoo_code VARCHAR(50) NULL,
    canonical_code VARCHAR(50) NULL,
    canonical_name VARCHAR(255) NULL,
    match_type VARCHAR(30) NOT NULL,
    confidence_score DECIMAL(5,2) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_general_ci;

ALTER TABLE product_catalog_mapping
ADD COLUMN domain VARCHAR(30) NOT NULL DEFAULT 'sales' AFTER source_system;

ALTER TABLE product_catalog_mapping
ADD UNIQUE KEY uq_product_catalog_mapping_sales (
    domain,
    wansoft_code,
    odoo_code,
    match_type
);
--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `backup_product_catalog_mapping`
--

CREATE TABLE IF NOT EXISTS backup_product_catalog_mapping AS
SELECT * FROM product_catalog_mapping;

--- actualizamos la tabla antes del backup 

ALTER TABLE product_catalog_mapping
ADD COLUMN lifecycle_status VARCHAR(30) NULL AFTER status,
ADD COLUMN replacement_group VARCHAR(255) NULL AFTER lifecycle_status,
ADD COLUMN replacement_score DECIMAL(5,2) NULL AFTER replacement_group,
ADD COLUMN replacement_reason VARCHAR(255) NULL AFTER replacement_score,
ADD COLUMN review_status VARCHAR(30) NULL AFTER replacement_reason;

--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `product_replacement_candidates`
--


CREATE TABLE IF NOT EXISTS product_replacement_candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_name_a VARCHAR(255),
    product_name_b VARCHAR(255),
    base_name VARCHAR(255),
    presentation_a VARCHAR(50),
    presentation_b VARCHAR(50),
    replacement_score DECIMAL(5,2),
    replacement_reason VARCHAR(255),
    recommended_lifecycle_a VARCHAR(30),
    recommended_lifecycle_b VARCHAR(30),
    review_status VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------


--
-- Estructura de tabla para la tabla `product_replacement_candidates`
--


CREATE TABLE IF NOT EXISTS product_replacement_candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_name_a VARCHAR(255),
    product_name_b VARCHAR(255),
    base_name VARCHAR(255),
    presentation_a VARCHAR(50),
    presentation_b VARCHAR(50),
    replacement_score DECIMAL(5,2),
    replacement_reason VARCHAR(255),
    recommended_lifecycle_a VARCHAR(30),
    recommended_lifecycle_b VARCHAR(30),
    review_status VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------


--
-- Estructura de tabla para la tabla `inventory_product_lifecycle`
--


CREATE TABLE IF NOT EXISTS inventory_product_lifecycle (
    id INT AUTO_INCREMENT PRIMARY KEY,
    CodigoProducto VARCHAR(50) NOT NULL,
    Producto VARCHAR(255) NULL,
    Departamento VARCHAR(255) NULL,
    CodigoDepartamento VARCHAR(50) NULL,
    UnidadDeMedida VARCHAR(100) NULL,
    current_stock_qty DECIMAL(18,4) NULL,
    last_activity_date DATETIME NULL,
    days_since_last_activity INT NULL,
    lifecycle_candidate VARCHAR(50) NOT NULL,
    source_logic VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_inventory_product_lifecycle (CodigoProducto)
);


--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------




--
-- Estructura de tabla para la tabla `odoo_inventory_raw_no_code_classification`
--


CREATE TABLE IF NOT EXISTS odoo_inventory_raw_no_code_classification (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category_name VARCHAR(255) NULL,
    sale_ok TINYINT(1) NOT NULL,
    purchase_ok TINYINT(1) NOT NULL,
    raw_classification VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------


--
-- Estructura de tabla para la tabla `inventory_bridge_report`
--

CREATE TABLE IF NOT EXISTS inventory_bridge_report (
    id INT AUTO_INCREMENT PRIMARY KEY,
    odoo_product_name VARCHAR(255) NOT NULL,
    odoo_category_name VARCHAR(255) NULL,
    raw_classification VARCHAR(100) NOT NULL,
    wansoft_code VARCHAR(50) NULL,
    wansoft_product_name VARCHAR(255) NULL,
    wansoft_department VARCHAR(255) NULL,
    wansoft_lifecycle_candidate VARCHAR(50) NULL,
    similarity_score DECIMAL(5,2) NULL,
    suggested_action VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------


--
-- Estructura de tabla para la tabla `inventory_mapping_dictionary`
--

CREATE TABLE IF NOT EXISTS inventory_mapping_dictionary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain VARCHAR(50) NOT NULL DEFAULT 'inventory',
    odoo_product_id BIGINT NULL,
    odoo_product_name VARCHAR(255) NOT NULL,
    odoo_category_name VARCHAR(255) NULL,
    wansoft_code VARCHAR(50) NULL,
    wansoft_product_name VARCHAR(255) NULL,
    wansoft_department VARCHAR(255) NULL,
    mapping_source VARCHAR(50) NOT NULL,
    mapping_status VARCHAR(50) NOT NULL,
    lifecycle_candidate VARCHAR(50) NULL,
    similarity_score DECIMAL(5,2) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_inventory_mapping_dictionary (domain, odoo_product_name, wansoft_code)
);


--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------


--
-- Indices de la tabla `odoo_inventory_raw_no_code_classification`
--
ALTER TABLE odoo_inventory_raw_no_code_classification
ADD COLUMN odoo_product_id BIGINT NULL AFTER id;

--
-- Indices de la tabla `inventory_bridge_report`
--
ALTER TABLE inventory_bridge_report
ADD COLUMN odoo_product_id BIGINT NULL AFTER id;


-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `odoo_inventory_snapshot`
--

CREATE TABLE IF NOT EXISTS odoo_inventory_snapshot (
    id INT AUTO_INCREMENT PRIMARY KEY,
    odoo_product_id BIGINT NULL,
    odoo_product_name VARCHAR(255) NOT NULL,
    product_code VARCHAR(100) NULL,
    source_location_id BIGINT NULL,
    location_name VARCHAR(255) NULL,
    stock_qty DECIMAL(18,4) NULL,

    mapping_found TINYINT(1) NOT NULL DEFAULT 0,
    lookup_method VARCHAR(50) NULL,
    mapping_status VARCHAR(50) NULL,
    usable_for_etl TINYINT(1) NOT NULL DEFAULT 0,

    wansoft_code VARCHAR(50) NULL,
    wansoft_product_name VARCHAR(255) NULL,
    wansoft_department VARCHAR(255) NULL,
    lifecycle_candidate VARCHAR(50) NULL,
    similarity_score DECIMAL(5,2) NULL,
    mapping_notes TEXT NULL,

    etl_loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_odoo_inventory_snapshot (odoo_product_id, source_location_id)
);


--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `odoo_inventory_snapshot`
--

CREATE TABLE IF NOT EXISTS odoo_inventory_backlog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    odoo_product_id BIGINT NULL,
    odoo_product_name VARCHAR(255) NOT NULL,
    product_code VARCHAR(100) NULL,
    source_location_id BIGINT NULL,
    location_name VARCHAR(255) NULL,
    stock_qty DECIMAL(18,4) NULL,

    mapping_found TINYINT(1) NOT NULL DEFAULT 0,
    lookup_method VARCHAR(50) NULL,
    mapping_status VARCHAR(50) NULL,
    usable_for_etl TINYINT(1) NOT NULL DEFAULT 0,

    wansoft_code VARCHAR(50) NULL,
    wansoft_product_name VARCHAR(255) NULL,
    wansoft_department VARCHAR(255) NULL,
    lifecycle_candidate VARCHAR(50) NULL,
    similarity_score DECIMAL(5,2) NULL,
    mapping_notes TEXT NULL,

    backlog_bucket VARCHAR(50) NOT NULL,
    etl_loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------

--
-- Indices de la tabla `inventory_mapping_dictionary`
--

ALTER TABLE inventory_mapping_dictionary
ADD COLUMN inventory_scope VARCHAR(50) NULL AFTER mapping_status,
ADD COLUMN scope_source VARCHAR(50) NULL AFTER inventory_scope,
ADD COLUMN scope_status VARCHAR(50) NULL AFTER scope_source;



-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `odoo_inventory_scope_classification`
--

CREATE TABLE IF NOT EXISTS odoo_inventory_scope_classification (
    id INT AUTO_INCREMENT PRIMARY KEY,
    odoo_product_id BIGINT NULL,
    product_name VARCHAR(255) NOT NULL,
    category_name VARCHAR(255) NULL,
    company_id_only BIGINT NULL,
    company_name VARCHAR(255) NULL,
    sale_ok TINYINT(1) NOT NULL,
    purchase_ok TINYINT(1) NOT NULL,
    inventory_scope VARCHAR(50) NOT NULL,
    scope_source VARCHAR(50) NOT NULL,
    scope_status VARCHAR(50) NOT NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_odoo_inventory_scope (odoo_product_id)
);


--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------

--
-- Indices de la tabla `odoo_inventory_scope_classification`
--
ALTER TABLE odoo_inventory_scope_classification
ADD COLUMN refined_inventory_scope VARCHAR(50) NULL AFTER inventory_scope,
ADD COLUMN refined_scope_source VARCHAR(50) NULL AFTER refined_inventory_scope,
ADD COLUMN refined_scope_status VARCHAR(50) NULL AFTER refined_scope_source;

--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `inventory_not_found_priority_backlog`
--

CREATE TABLE IF NOT EXISTS inventory_not_found_priority_backlog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    odoo_product_id BIGINT NOT NULL,
    odoo_product_name VARCHAR(255) NOT NULL,
    category_name VARCHAR(255) NULL,
    refined_inventory_scope VARCHAR(50) NULL,
    not_found_classification VARCHAR(100) NOT NULL,
    row_count INT NOT NULL,
    location_count INT NOT NULL,
    total_abs_stock_qty DECIMAL(18,4) NULL,
    priority_bucket VARCHAR(20) NOT NULL,
    priority_reason VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_inventory_not_found_priority (odoo_product_id)
);

--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `inventory_not_found_p1_bridge`
--

CREATE TABLE IF NOT EXISTS inventory_not_found_p1_bridge (
    id INT AUTO_INCREMENT PRIMARY KEY,
    odoo_product_id BIGINT NOT NULL,
    odoo_product_name VARCHAR(255) NOT NULL,
    category_name VARCHAR(255) NULL,
    wansoft_code VARCHAR(50) NULL,
    wansoft_product_name VARCHAR(255) NULL,
    wansoft_department VARCHAR(255) NULL,
    lifecycle_candidate VARCHAR(50) NULL,
    similarity_score DECIMAL(5,2) NULL,
    suggested_action VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_inventory_not_found_p1_bridge (odoo_product_id, wansoft_code)
);

--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `inventory_not_found_p2_bridge`
--

CREATE TABLE IF NOT EXISTS inventory_not_found_p2_bridge (
    id INT AUTO_INCREMENT PRIMARY KEY,
    odoo_product_id BIGINT NOT NULL,
    odoo_product_name VARCHAR(255) NOT NULL,
    category_name VARCHAR(255) NULL,
    wansoft_code VARCHAR(50) NULL,
    wansoft_product_name VARCHAR(255) NULL,
    wansoft_department VARCHAR(255) NULL,
    lifecycle_candidate VARCHAR(50) NULL,
    similarity_score DECIMAL(5,2) NULL,
    suggested_action VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_inventory_not_found_p2_bridge (odoo_product_id, wansoft_code)
);


--
-- Índices para tablas volcadas
--


-- --------------------------------------------------------


--
-- Indices de la tabla `costeomensual`
--
ALTER TABLE `costeomensual`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `costeomensual_semanapyq`
--
ALTER TABLE `costeomensual_semanapyq`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `getallordenesbyday_detalleventa`
--
ALTER TABLE `getallordenesbyday_detalleventa`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `Sucursal` (`Sucursal`,`Movimiento_Id`,`Hora`);

--
-- Indices de la tabla `getallordenesbyday_modificador`
--
ALTER TABLE `getallordenesbyday_modificador`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `Movimiento_Id` (`Movimiento_Id`,`Sucursal`,`Hora`);

--
-- Indices de la tabla `getallordenesbyday_new_detalleventa`
--
ALTER TABLE `getallordenesbyday_new_detalleventa`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `Movimiento_Id` (`Movimiento_Id`,`Sucursal`,`Hora`,`ComandaId`);

--
-- Indices de la tabla `getallordenesbyday_new_modificador`
--
ALTER TABLE `getallordenesbyday_new_modificador`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `Movimiento_Id` (`Movimiento_Id`,`Sucursal`,`Hora`,`Descripcion`);

--
-- Indices de la tabla `getallordenesbyday_new_pago`
--
ALTER TABLE `getallordenesbyday_new_pago`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `Pagos_Id` (`Pagos_Id`,`Sucursal`);

--
-- Indices de la tabla `getallordenesbyday_new_pagos`
--
ALTER TABLE `getallordenesbyday_new_pagos`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `Pagos_Id` (`Pagos_Id`,`Sucursal`);

--
-- Indices de la tabla `getallordenesbyday_new_venta`
--
ALTER TABLE `getallordenesbyday_new_venta`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `Movimento` (`Movimento`,`Sucursal`);

--
-- Indices de la tabla `getallordenesbyday_venta`
--
ALTER TABLE `getallordenesbyday_venta`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `Movimento` (`Movimento`,`Sucursal`);

--
-- Indices de la tabla `getcostreport`
--
ALTER TABLE `getcostreport`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `getexpensesbyinputdate`
--
ALTER TABLE `getexpensesbyinputdate`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `getglobalcashclosing`
--
ALTER TABLE `getglobalcashclosing`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `getinputinventory_entrada`
--
ALTER TABLE `getinputinventory_entrada`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `getoutgoinginventory_salida`
--
ALTER TABLE `getoutgoinginventory_salida`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `getpendingpurchaseorders`
--
ALTER TABLE `getpendingpurchaseorders`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `getpendingpurchaseorders_details`
--
ALTER TABLE `getpendingpurchaseorders_details`
  ADD PRIMARY KEY (`id`),
  ADD KEY `orden_id` (`orden_id`);

--
-- Indices de la tabla `getstockinventory_inventario`
--
ALTER TABLE `getstockinventory_inventario`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `IdProducto` (`IdProducto`,`Sucursal`,`Fecha`);

--
-- Indices de la tabla `gettablajeriareport`
--
ALTER TABLE `gettablajeriareport`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `gettotalcostbydate`
--
ALTER TABLE `gettotalcostbydate`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `costeomensual`
--
ALTER TABLE `costeomensual`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `costeomensual_semanapyq`
--
ALTER TABLE `costeomensual_semanapyq`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getallordenesbyday_detalleventa`
--
ALTER TABLE `getallordenesbyday_detalleventa`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getallordenesbyday_modificador`
--
ALTER TABLE `getallordenesbyday_modificador`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getallordenesbyday_new_detalleventa`
--
ALTER TABLE `getallordenesbyday_new_detalleventa`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getallordenesbyday_new_modificador`
--
ALTER TABLE `getallordenesbyday_new_modificador`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getallordenesbyday_new_pago`
--
ALTER TABLE `getallordenesbyday_new_pago`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getallordenesbyday_new_pagos`
--
ALTER TABLE `getallordenesbyday_new_pagos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getallordenesbyday_new_venta`
--
ALTER TABLE `getallordenesbyday_new_venta`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getallordenesbyday_venta`
--
ALTER TABLE `getallordenesbyday_venta`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getcostreport`
--
ALTER TABLE `getcostreport`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getexpensesbyinputdate`
--
ALTER TABLE `getexpensesbyinputdate`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getglobalcashclosing`
--
ALTER TABLE `getglobalcashclosing`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getinputinventory_entrada`
--
ALTER TABLE `getinputinventory_entrada`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getoutgoinginventory_salida`
--
ALTER TABLE `getoutgoinginventory_salida`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getpendingpurchaseorders`
--
ALTER TABLE `getpendingpurchaseorders`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getpendingpurchaseorders_details`
--
ALTER TABLE `getpendingpurchaseorders_details`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `getstockinventory_inventario`
--
ALTER TABLE `getstockinventory_inventario`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `gettablajeriareport`
--
ALTER TABLE `gettablajeriareport`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `gettotalcostbydate`
--
ALTER TABLE `gettotalcostbydate`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `getpendingpurchaseorders_details`
--
ALTER TABLE `getpendingpurchaseorders_details`
  ADD CONSTRAINT `getpendingpurchaseorders_details_ibfk_1` FOREIGN KEY (`orden_id`) REFERENCES `getpendingpurchaseorders` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
