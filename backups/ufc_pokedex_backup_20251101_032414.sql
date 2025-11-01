--
-- PostgreSQL database dump
--

\restrict 6Ak1GyBa1elHE0QaGIdbcknqpbIiFeSwgb9CWRwdH91B6IdhN1fy5EMf9HrfBG9

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: ufc_pokedex
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO ufc_pokedex;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: ufc_pokedex
--

COMMENT ON SCHEMA public IS '';


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: ufc_pokedex
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- PostgreSQL database dump complete
--

\unrestrict 6Ak1GyBa1elHE0QaGIdbcknqpbIiFeSwgb9CWRwdH91B6IdhN1fy5EMf9HrfBG9

