-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: localhost    Database: enrollmentsystem
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `assign`
--

DROP TABLE IF EXISTS `assign`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `assign` (
  `SubjID` int NOT NULL,
  `TID` int NOT NULL,
  UNIQUE KEY `SubjID` (`SubjID`),
  KEY `TID` (`TID`),
  CONSTRAINT `assign_ibfk_1` FOREIGN KEY (`SubjID`) REFERENCES `subjects` (`subjid`),
  CONSTRAINT `assign_ibfk_2` FOREIGN KEY (`TID`) REFERENCES `teachers` (`tid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assign`
--

LOCK TABLES `assign` WRITE;
/*!40000 ALTER TABLE `assign` DISABLE KEYS */;
/*!40000 ALTER TABLE `assign` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `enroll`
--

DROP TABLE IF EXISTS `enroll`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `enroll` (
  `eid` int NOT NULL AUTO_INCREMENT,
  `studid` int DEFAULT NULL,
  `subjid` int DEFAULT NULL,
  `evaluation` text,
  PRIMARY KEY (`eid`),
  UNIQUE KEY `studid` (`studid`,`subjid`),
  KEY `subjid` (`subjid`),
  CONSTRAINT `enroll_ibfk_1` FOREIGN KEY (`studid`) REFERENCES `students` (`studid`),
  CONSTRAINT `enroll_ibfk_2` FOREIGN KEY (`subjid`) REFERENCES `subjects` (`subjid`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `enroll`
--

LOCK TABLES `enroll` WRITE;
/*!40000 ALTER TABLE `enroll` DISABLE KEYS */;
/*!40000 ALTER TABLE `enroll` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `grades`
--

DROP TABLE IF EXISTS `grades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `grades` (
  `gradeid` int NOT NULL AUTO_INCREMENT,
  `enroll_eid` int NOT NULL,
  `prelim` text,
  `midterm` text,
  `prefinal` text,
  `final` text,
  PRIMARY KEY (`gradeid`),
  UNIQUE KEY `enroll_eid` (`enroll_eid`),
  CONSTRAINT `grades_ibfk_1` FOREIGN KEY (`enroll_eid`) REFERENCES `enroll` (`eid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `grades`
--

LOCK TABLES `grades` WRITE;
/*!40000 ALTER TABLE `grades` DISABLE KEYS */;
/*!40000 ALTER TABLE `grades` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `students`
--

DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `students` (
  `studid` int NOT NULL,
  `studname` text NOT NULL,
  `studadd` text,
  `studcrs` text,
  `studgender` text,
  `yrlvl` text,
  PRIMARY KEY (`studid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `students`
--

LOCK TABLES `students` WRITE;
/*!40000 ALTER TABLE `students` DISABLE KEYS */;
INSERT INTO `students` VALUES (1000,'213','123','123','123','2'),(1001,'123123','12323','23','245','23'),(1002,'234','d','d','d','2'),(1003,'123123','12323','23','245','23');
/*!40000 ALTER TABLE `students` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `subjects`
--

DROP TABLE IF EXISTS `subjects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subjects` (
  `subjid` int NOT NULL,
  `subjcode` text,
  `subjdesc` text,
  `subjunits` int DEFAULT NULL,
  `subjsched` text,
  PRIMARY KEY (`subjid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `subjects`
--

LOCK TABLES `subjects` WRITE;
/*!40000 ALTER TABLE `subjects` DISABLE KEYS */;
INSERT INTO `subjects` VALUES (2000,'aa','aa',12,'MWF 08:20-09:20'),(2001,'bb','bb',5,'MWF 11:35-12:35'),(2002,'cc','cc',3,'MWF 10:30-11:30'),(2003,'dd','dd',3,'TTH 10:30-11:30'),(2004,'ee','ee',2,'MWF 09:30-10:25'),(2005,'ff','ff',5,'TTH 08:20-09:20'),(2006,'gg','gg',3,'TTH 09:30-10:25'),(2007,'hh','hh',12,'MWF 11:00-12:00'),(2008,'ii','ii',2,'MWF 09:00-11:00'),(2009,'kk','kk',5,'TTH 10:40-11:25');
/*!40000 ALTER TABLE `subjects` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `teachers`
--

DROP TABLE IF EXISTS `teachers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `teachers` (
  `tid` int NOT NULL,
  `tname` text,
  `tdept` text,
  `tadd` text,
  `tcontact` text,
  `tstatus` text,
  PRIMARY KEY (`tid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `teachers`
--

LOCK TABLES `teachers` WRITE;
/*!40000 ALTER TABLE `teachers` DISABLE KEYS */;
INSERT INTO `teachers` VALUES (3000,'a','a','a','a','a'),(3001,'x','x','x','x','x'),(3002,'a','a','a','a','a');
/*!40000 ALTER TABLE `teachers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'enrollmentsystem'
--
/*!50003 DROP PROCEDURE IF EXISTS `checkconflict` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = cp932 */ ;
/*!50003 SET character_set_results = cp932 */ ;
/*!50003 SET collation_connection  = cp932_japanese_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`root`@`localhost` PROCEDURE `checkconflict`(in param_studid int, in param_subjid int, out result varchar(25))
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE j INT;
    DECLARE n INT;
    DECLARE a TEXT;
    DECLARE b TEXT;

    DECLARE newdays VARCHAR(5);
    DECLARE newstart VARCHAR(5);
    DECLARE newend VARCHAR(5);

    DECLARE olddays VARCHAR(5);
    DECLARE oldstart VARCHAR(5);
    DECLARE oldend VARCHAR(5);

    DROP TEMPORARY TABLE IF EXISTS oldsched;
    CREATE TABLE oldsched (
        id INT AUTO_INCREMENT PRIMARY KEY,
        osched text
    );

    
    INSERT INTO oldsched(osched) 
    SELECT subjsched FROM subjects 
    INNER JOIN enroll ON subjects.subjid = enroll.subjid
    WHERE enroll.studid = param_studid;

    
    
    SELECT 
        LEFT(subjsched,3), 
        SUBSTRING(subjsched,5,5), 
        SUBSTRING(subjsched,11,5) 
    INTO newdays, newstart, newend
    FROM subjects WHERE subjid = param_subjid;

    SELECT COUNT(*) INTO n FROM oldsched;

    SET result = '';

    WHILE i <= n DO
        SET j = 1;

        WHILE j < n DO
            SELECT osched INTO a FROM oldsched WHERE id = j;
            SELECT osched INTO b FROM oldsched WHERE id = j + 1;

            IF a > b THEN
                UPDATE oldsched SET osched = b WHERE id = j;
                UPDATE oldsched SET osched = a WHERE id = j + 1;
            END IF;

            SET j = j + 1;
        END WHILE;

        
        
        SELECT 
            LEFT(osched,3),
            SUBSTRING(osched,5,5),
            SUBSTRING(osched,11,5)
        INTO olddays, oldstart, oldend
        FROM oldsched
        WHERE id = i;

        SET oldstart = STR_TO_DATE(oldstart, '%H:%i');
        SET oldend   = STR_TO_DATE(oldend, '%H:%i');
        SET newstart = STR_TO_DATE(newstart, '%H:%i');
        SET newend   = STR_TO_DATE(newend, '%H:%i');

        
        
        IF(olddays = newdays) THEN
            IF(oldstart < newend AND oldend > newstart) THEN
                SET result = CONCAT('Conflict with ', olddays, ' ', oldstart, '-', oldend);
            END IF;
        END IF;

        SET i = i + 1;
    END WHILE;
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-29 22:30:06
