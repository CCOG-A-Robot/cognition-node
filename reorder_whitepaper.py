import re

with open("WHITEPAPER_v0.3.md", "r") as f:
    text = f.read()

# Extract sections
# Find the start of Conclusion
conc_idx = text.find("## 6. Conclusion")
econ_idx = text.find("## 7. Economics & Network Fees")

if conc_idx != -1 and econ_idx != -1:
    before_conc = text[:conc_idx]
    conc_text = text[conc_idx:econ_idx]
    econ_text = text[econ_idx:]
    
    # Rename the numbers
    conc_text = conc_text.replace("## 6. Conclusion", "## 7. Conclusion")
    econ_text = econ_text.replace("## 7. Economics & Network Fees", "## 6. Economics & Network Fees")
    
    new_text = before_conc + econ_text + "\n\n" + conc_text
    
    with open("WHITEPAPER_v0.3.md", "w") as f:
        f.write(new_text.strip() + "\n")
