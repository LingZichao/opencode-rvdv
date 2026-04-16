    ## Condition Coverage Rules:
    
    ### OR Logic (A | B)
    | A | B | Result | Covered? | Note |
    |---|---|--------|----------|------|
    | 0 | 0 | 0 | ✅ Yes | Both false → result false |
    | 0 | 1 | 1 | ✅ Yes | B true → result true |
    | 1 | 0 | 1 | ✅ Yes | A true → result true |
    | 1 | 1 | 1 | ❌ **Skipped** | Redundant (already true with A=1) |
    
    **Rule**: When A=1, the result is already determined as true, so A=1 & B=1 is not evaluated.
    
    ### AND Logic (A & B)
    | A | B | Result | Covered? | Note |
    |---|---|--------|----------|------|
    | 0 | 0 | 0 | ❌ **Skipped** | Redundant (already false with A=0) |
    | 0 | 1 | 0 | ✅ Yes | A false → result false |
    | 1 | 0 | 0 | ✅ Yes | B false → result false |
    | 1 | 1 | 1 | ✅ Yes | Both true → result true |
    
    **Rule**: When A=0, the result is already determined as false, so A=0 & B=0 is not evaluated.
    
    ### Example:
    ```verilog
    // Condition: (a > b) | (c == d)
    if ((a > b) | (c == d)) begin
        // ...
    end
    
    // Condition coverage evaluates:
    // 1. (a > b)=0, (c == d)=0 → condition = 0
    // 2. (a > b)=0, (c == d)=1 → condition = 1
    // 3. (a > b)=1, (c == d)=0 → condition = 1
    // 4. (a > b)=1, (c == d)=1 → SKIPPED (redundant)
    
    // Condition: (x_valid) & (y_ready)
    if ((x_valid) & (y_ready)) begin
        // ...
    end
    
    // Condition coverage evaluates:
    // 1. (x_valid)=0, (y_ready)=1 → condition = 0
    // 2. (x_valid)=1, (y_ready)=0 → condition = 0
    // 3. (x_valid)=1, (y_ready)=1 → condition = 1
    // 4. (x_valid)=0, (y_ready)=0 → SKIPPED (redundant)