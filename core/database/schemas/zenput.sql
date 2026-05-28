-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 28-05-2026 a las 20:55:39
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
-- Base de datos: `zenput`
--
CREATE DATABASE IF NOT EXISTS `zenput` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `zenput`;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `form_templates`
--

CREATE TABLE `form_templates` (
  `form_id` int(11) NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `num_submissions` int(11) DEFAULT NULL,
  `date_created` datetime DEFAULT NULL,
  `date_last_submitted` datetime DEFAULT NULL,
  `creator_full_name` varchar(255) DEFAULT NULL,
  `category_name` varchar(255) DEFAULT NULL,
  `last_updated` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `submissions`
--

CREATE TABLE `submissions` (
  `submission_id` varchar(255) NOT NULL,
  `form_template_id` int(11) DEFAULT NULL,
  `location_name` varchar(255) DEFAULT NULL,
  `user_display_name` varchar(255) DEFAULT NULL,
  `date_submitted` datetime DEFAULT NULL,
  `time_to_complete` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `submission_answers`
--

CREATE TABLE `submission_answers` (
  `answer_id` int(11) NOT NULL,
  `submission_id` varchar(255) DEFAULT NULL,
  `field_id` int(11) DEFAULT NULL,
  `title` text DEFAULT NULL,
  `field_type` varchar(50) DEFAULT NULL,
  `value_as_string` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `zenput_tasks`
--

CREATE TABLE `zenput_tasks` (
  `task_id` int(11) NOT NULL,
  `title` text DEFAULT NULL,
  `description` text DEFAULT NULL,
  `company_id` int(11) DEFAULT NULL,
  `account_id` int(11) DEFAULT NULL,
  `account_name` varchar(255) DEFAULT NULL,
  `account_address` text DEFAULT NULL,
  `account_city` varchar(100) DEFAULT NULL,
  `account_state` varchar(100) DEFAULT NULL,
  `account_zipcode` varchar(20) DEFAULT NULL,
  `account_country` varchar(10) DEFAULT NULL,
  `account_lat` decimal(10,8) DEFAULT NULL,
  `account_lon` decimal(11,8) DEFAULT NULL,
  `status_id` int(11) DEFAULT NULL,
  `status_type` varchar(50) DEFAULT NULL,
  `status_name` varchar(50) DEFAULT NULL,
  `reply_type` varchar(50) DEFAULT NULL,
  `reporter_id` int(11) DEFAULT NULL,
  `reporter_display_name` varchar(255) DEFAULT NULL,
  `assignee_id` int(11) DEFAULT NULL,
  `assignee_display_name` varchar(255) DEFAULT NULL,
  `date_created` datetime DEFAULT NULL,
  `date_modified` datetime DEFAULT NULL,
  `date_start` datetime DEFAULT NULL,
  `date_due` datetime DEFAULT NULL,
  `time_zone` varchar(100) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `is_closed` tinyint(1) DEFAULT NULL,
  `project_id` int(11) DEFAULT NULL,
  `fulfillment_type` varchar(50) DEFAULT NULL,
  `fulfillment_date_completed` datetime DEFAULT NULL,
  `fulfillment_date_submitted` datetime DEFAULT NULL,
  `fulfillment_user_id` int(11) DEFAULT NULL,
  `fulfillment_user_display_name` varchar(255) DEFAULT NULL,
  `fulfillment_fields` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`fulfillment_fields`)),
  `date_submitted` datetime DEFAULT NULL,
  `deleted` tinyint(1) DEFAULT NULL,
  `num_comments` int(11) DEFAULT NULL,
  `is_completed_late` tinyint(1) DEFAULT NULL,
  `current_state` varchar(50) DEFAULT NULL,
  `subscribers` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`subscribers`)),
  `last_updated` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `form_templates`
--
ALTER TABLE `form_templates`
  ADD PRIMARY KEY (`form_id`);

--
-- Indices de la tabla `submissions`
--
ALTER TABLE `submissions`
  ADD PRIMARY KEY (`submission_id`),
  ADD KEY `form_template_id` (`form_template_id`);

--
-- Indices de la tabla `submission_answers`
--
ALTER TABLE `submission_answers`
  ADD PRIMARY KEY (`answer_id`),
  ADD KEY `submission_id` (`submission_id`);

--
-- Indices de la tabla `zenput_tasks`
--
ALTER TABLE `zenput_tasks`
  ADD PRIMARY KEY (`task_id`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `submission_answers`
--
ALTER TABLE `submission_answers`
  MODIFY `answer_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `submissions`
--
ALTER TABLE `submissions`
  ADD CONSTRAINT `submissions_ibfk_1` FOREIGN KEY (`form_template_id`) REFERENCES `form_templates` (`form_id`);

--
-- Filtros para la tabla `submission_answers`
--
ALTER TABLE `submission_answers`
  ADD CONSTRAINT `submission_answers_ibfk_1` FOREIGN KEY (`submission_id`) REFERENCES `submissions` (`submission_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
