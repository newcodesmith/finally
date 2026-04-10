# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: chatdiag.spec.ts >> chat panel opens and works
- Location: e2e/chatdiag.spec.ts:3:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: page.waitForTimeout: Test timeout of 60000ms exceeded.
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - banner [ref=e3]:
      - generic [ref=e4]: FinAlly
      - generic [ref=e5]:
        - generic [ref=e6]: $10,000.00
        - generic [ref=e8]: Cash
        - generic [ref=e9]: $10,000.00
        - generic "Connected" [ref=e10]
    - generic [ref=e12]:
      - complementary [ref=e13]:
        - generic [ref=e14]:
          - generic [ref=e15]: Watchlist
          - generic [ref=e16]:
            - button "$268.96 -0.13%" [ref=e17]:
              - generic [ref=e18]: $268.96
              - generic [ref=e19]: "-0.13%"
            - button "0 $142.23 -0.03%" [ref=e22]:
              - generic [ref=e23]: "0"
              - generic [ref=e24]: $142.23
              - generic [ref=e25]: "-0.03%"
            - button "AAPL $189.98 -0.01%" [ref=e28]:
              - generic [ref=e29]: AAPL
              - generic [ref=e30]: $189.98
              - generic [ref=e31]: "-0.01%"
            - button "AMZN $185.02 +0.01%" [ref=e34]:
              - generic [ref=e35]: AMZN
              - generic [ref=e36]: $185.02
              - generic [ref=e37]: +0.01%
            - button "GOOGL $175.01 +0.01%" [ref=e40]:
              - generic [ref=e41]: GOOGL
              - generic [ref=e42]: $175.01
              - generic [ref=e43]: +0.01%
            - button "JPM $194.84 -0.08%" [ref=e46]:
              - generic [ref=e47]: JPM
              - generic [ref=e48]: $194.84
              - generic [ref=e49]: "-0.08%"
            - button "META $500.52 +0.10%" [ref=e52]:
              - generic [ref=e53]: META
              - generic [ref=e54]: $500.52
              - generic [ref=e55]: +0.10%
            - button "MSFT $419.92 -0.02%" [ref=e58]:
              - generic [ref=e59]: MSFT
              - generic [ref=e60]: $419.92
              - generic [ref=e61]: "-0.02%"
            - button "NVDA $797.25 -0.34%" [ref=e64]:
              - generic [ref=e65]: NVDA
              - generic [ref=e66]: $797.25
              - generic [ref=e67]: "-0.34%"
            - button "PYPL $134.39 +2.62%" [ref=e70]:
              - generic [ref=e71]: PYPL
              - generic [ref=e72]: $134.39
              - generic [ref=e73]: +2.62%
            - button "TSLA $249.48 -0.21%" [ref=e76]:
              - generic [ref=e77]: TSLA
              - generic [ref=e78]: $249.48
              - generic [ref=e79]: "-0.21%"
            - button "V $279.69 -0.11%" [ref=e82]:
              - generic [ref=e83]: V
              - generic [ref=e84]: $279.69
              - generic [ref=e85]: "-0.11%"
      - main [ref=e88]:
        - generic [ref=e91]:
          - generic [ref=e92]: "0"
          - generic [ref=e93]: $142.23
        - generic [ref=e95]:
          - generic [ref=e97]: No positions yet — buy something to get started
          - generic [ref=e101]: No positions
        - generic [ref=e102]:
          - textbox "Ticker" [ref=e103]
          - spinbutton [ref=e104]
          - button "Buy" [disabled] [ref=e105]
          - button "Sell" [disabled] [ref=e106]
    - button "Open AI Assistant" [ref=e107]:
      - img [ref=e108]
  - alert [ref=e110]
```