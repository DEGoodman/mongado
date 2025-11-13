---
id: 13
title: Syntax Highlighting Test
date: 2025-11-13
tags: [test, development]
summary: A test article to demonstrate syntax highlighting in code blocks
draft: true
---

# Syntax Highlighting Test

This article tests the syntax highlighting feature for code blocks.

## Python Example

```python
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# Test the function
result = fibonacci(10)
print(f"The 10th Fibonacci number is: {result}")
```

## JavaScript Example

```javascript
const fetchData = async (url) => {
  try {
    const response = await fetch(url);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching data:", error);
    throw error;
  }
};

// Usage
fetchData("https://api.example.com/data")
  .then((data) => console.log(data));
```

## TypeScript Example

```typescript
interface User {
  id: number;
  name: string;
  email: string;
}

class UserService {
  private users: User[] = [];

  addUser(user: User): void {
    this.users.push(user);
  }

  findUserById(id: number): User | undefined {
    return this.users.find((user) => user.id === id);
  }
}

const service = new UserService();
service.addUser({ id: 1, name: "John Doe", email: "john@example.com" });
```

## Bash Example

```bash
#!/bin/bash

# Deploy script
ENVIRONMENT=$1

if [ -z "$ENVIRONMENT" ]; then
    echo "Usage: $0 <environment>"
    exit 1
fi

echo "Deploying to $ENVIRONMENT..."
docker compose up -d --build
docker compose logs -f
```

## JSON Example

```json
{
  "name": "mongado",
  "version": "1.0.0",
  "description": "Personal knowledge base",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "react": "^18.0.0",
    "next": "^14.0.0"
  }
}
```

## Inline Code

This is `inline code` which should not have syntax highlighting but should have a light background.

## Plain Code Block

```
This is a plain code block without a language specified.
It should use the default styling.
No syntax highlighting here.
```

## Summary

The syntax highlighting feature supports multiple programming languages including Python, JavaScript, TypeScript, Bash, JSON, and many more. Code blocks with specified languages get proper syntax highlighting, while inline code maintains its simple styling.
