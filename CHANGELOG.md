# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-01-05

### Fixed
- **Telegram Notifications**: Fixed a `400 Bad Request` error caused by unescaped dots in price/score numbers when using Telegram's MarkdownV2 format.

## [1.0.0] - 2026-01-05

### Added
- Initial public release.
- **Scanner Core**: High-performance batch scanning for US equities.
- **Data Providers**: Full support for Alpaca (primary), Alpha Vantage, Finnhub, and Twelve Data.
- **UI**: Interactive Streamlit web interface with charting and manual scanning.
- **Strategy**: Momentum strategy using RSI, EMA, MACD, Volume, and ADX.
- **Safety**: Built-in verification scripts (`verify-safety.sh`) to prevent secret leaks.
