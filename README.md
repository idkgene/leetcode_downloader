# LeetCode Submission Scraper

A Python tool for automatically downloading and organizing your LeetCode submissions. This scraper helps you maintain a local backup of all your LeetCode solutions while organizing them in a clean, searchable structure.

![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Selenium](https://img.shields.io/badge/selenium-4.0%2B-orange)

## 📋 Prerequisites

- Python
- Chrome browser installed
- Stable internet connection

## 💻 Usage

1. Run the scraper:

```bash
python lcus_submission.py
```

2. Enter your LeetCode credentials when prompted

3. Complete the Cloudflare verification if requested

4. Wait for the scraper to download your submissions

## 📁 Directory Structure

```
leetcode-submission-scraper/
├── lcus_[username]/           # All submissions by problem
│   ├── two-sum/              # Problem-specific directory
│   │   ├── 1234567890.json   # Full submission data
│   │   └── ...
│   └── ...
├── Accepted/                  # Latest accepted solutions
│   ├── two-sum.py
│   ├── add-two-numbers.cpp
│   └── ...
└── logs/                     # Detailed operation logs
    └── leetcode_scraper_YYYYMMDD_HHMMSS.log
```

## 🛡️ Security

- Credentials are never stored
- Session handling is secure
- No API keys required

## 📝 Logging

The scraper maintains detailed logs at multiple levels:
- Console: Basic progress information
- Log File: Detailed debug information
- Screenshots: Captured on critical errors

## ⚠️ Known Limitations

- Requires manual Cloudflare verification
- Rate limiting may affect large-scale downloads
- Some language-specific features may need manual configuration

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
