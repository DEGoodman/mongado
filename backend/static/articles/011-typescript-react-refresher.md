---
id: 11
title: "TypeScript & React Refresher"
summary: "Quick reference guide covering TypeScript fundamentals, advanced patterns, React hooks, performance optimization, and practical exercises. A condensed resource for refreshing frontend development skills."
url: ""
tags: ["typescript", "react", "reference", "webdev"]
draft: false
published_date: "2025-11-12T10:00:00"
created_at: "2025-11-12T10:00:00"
---

**Purpose**: Quick reference guide to refresh TypeScript and React fundamentals

---

## Table of Contents

1. [TypeScript Fundamentals](#typescript-fundamentals)
2. [TypeScript Advanced Patterns](#typescript-advanced-patterns)
3. [React Fundamentals](#react-fundamentals)
4. [React Hooks Deep Dive](#react-hooks-deep-dive)
5. [React Performance Patterns](#react-performance-patterns)
6. [Quick Reference](#quick-reference)
7. [Practice Exercises](#practice-exercises)

---

## TypeScript Fundamentals

### Basic Types

```typescript
// Primitive types
const productName: string = "Laptop";
const price: number = 999.99;
const inStock: boolean = true;
const releaseDate: Date = new Date();

// Arrays
const tags: string[] = ["electronics", "computers"];
const prices: Array<number> = [99.99, 199.99, 299.99];

// Tuples (fixed-length arrays with specific types)
const product: [string, number] = ["Laptop", 999.99];

// Any (avoid when possible!)
const legacy: any = "could be anything";

// Unknown (safer than any)
const userInput: unknown = getUserInput();
if (typeof userInput === "string") {
  console.log(userInput.toUpperCase()); // Type guard required
}

// Void (function returns nothing)
function logProduct(name: string): void {
  console.log(name);
}

// Never (function never returns)
function throwError(message: string): never {
  throw new Error(message);
}

// Null and undefined
const optional: string | null = null;
const maybe: string | undefined = undefined;
```

---

### Interfaces vs Types

**Both define object shapes, but with subtle differences.**

#### Interfaces

```typescript
// Interface - can be extended and merged
interface Product {
  id: string;
  name: string;
  price: number;
  category: string;
  inStock: boolean;
}

// Extending interfaces
interface ProductWithReviews extends Product {
  reviews: Review[];
  averageRating: number;
}

// Interface merging (declaration merging)
interface Product {
  createdAt: Date; // Automatically merges with above
}

// Implementing interfaces in classes
class PhysicalProduct implements Product {
  id: string;
  name: string;
  price: number;
  category: string;
  inStock: boolean;

  constructor(data: Product) {
    this.id = data.id;
    this.name = data.name;
    this.price = data.price;
    this.category = data.category;
    this.inStock = data.inStock;
  }
}
```

#### Types (Type Aliases)

```typescript
// Type alias - more flexible, can't be merged
type Product = {
  id: string;
  name: string;
  price: number;
  category: string;
  inStock: boolean;
};

// Union types (OR)
type Status = "pending" | "processing" | "shipped" | "delivered";
type PaymentMethod = "credit_card" | "paypal" | "crypto";

// Intersection types (AND)
type BaseProduct = {
  id: string;
  name: string;
};

type PricedProduct = {
  price: number;
  currency: string;
};

type Product = BaseProduct & PricedProduct;
// Result: { id, name, price, currency }

// Type aliases for functions
type PriceCalculator = (price: number, taxRate: number) => number;

const calculateTotal: PriceCalculator = (price, taxRate) => {
  return price * (1 + taxRate);
};

// Complex union types
type ApiResponse<T> =
  | { success: true; data: T }
  | { success: false; error: string };

const response: ApiResponse<Product> = {
  success: true,
  data: { id: "1", name: "Laptop", price: 999 }
};
```

#### When to Use Which?

**Use Interface when**:
- Defining object shapes
- Need to extend (inheritance)
- Working with classes
- Want declaration merging

**Use Type when**:
- Union types (`|`)
- Intersection types (`&`)
- Mapped types
- Conditional types
- Aliasing primitives

**Practical guideline**: Use `interface` for React component props and API data models, use `type` for unions and complex type transformations.

---

### Optional and Readonly

```typescript
interface Product {
  id: string;
  name: string;
  price: number;
  description?: string;        // Optional property
  readonly createdAt: Date;    // Cannot be modified after creation
}

const product: Product = {
  id: "1",
  name: "Laptop",
  price: 999,
  createdAt: new Date()
};

// product.createdAt = new Date(); // ❌ Error: readonly
product.price = 899; // ✅ OK

// Readonly utility type
type ReadonlyProduct = Readonly<Product>;

const immutableProduct: ReadonlyProduct = {
  id: "1",
  name: "Laptop",
  price: 999,
  createdAt: new Date()
};

// immutableProduct.price = 899; // ❌ Error: all properties are readonly
```

---

## TypeScript Advanced Patterns

### Generics

**Generics allow you to write reusable, type-safe code.**

```typescript
// Generic function
function getFirstItem<T>(items: T[]): T | undefined {
  return items[0];
}

const firstProduct = getFirstItem<Product>(products);  // Type: Product | undefined
const firstName = getFirstItem<string>(["Alice", "Bob"]); // Type: string | undefined
const firstNumber = getFirstItem([1, 2, 3]); // Type inference: number | undefined

// Generic interface
interface ApiResponse<T> {
  data: T;
  status: number;
  message: string;
}

const productResponse: ApiResponse<Product> = {
  data: { id: "1", name: "Laptop", price: 999 },
  status: 200,
  message: "Success"
};

const productsResponse: ApiResponse<Product[]> = {
  data: [/* products */],
  status: 200,
  message: "Success"
};

// Generic with constraints
interface HasId {
  id: string;
}

function findById<T extends HasId>(items: T[], id: string): T | undefined {
  return items.find(item => item.id === id);
}

// Works with any type that has an id
const product = findById(products, "123");
const user = findById(users, "456");

// Multiple type parameters
function merge<T, U>(obj1: T, obj2: U): T & U {
  return { ...obj1, ...obj2 };
}

const merged = merge(
  { name: "Laptop" },
  { price: 999 }
); // Type: { name: string } & { price: number }

// Generic React component
interface ListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
}

function List<T>({ items, renderItem }: ListProps<T>) {
  return (
    <ul>
      {items.map((item, index) => (
        <li key={index}>{renderItem(item)}</li>
      ))}
    </ul>
  );
}

// Usage
<List
  items={products}
  renderItem={(product) => <ProductCard product={product} />}
/>
```

---

### Utility Types

**TypeScript provides built-in utility types for common transformations.**

```typescript
interface Product {
  id: string;
  name: string;
  price: number;
  description: string;
  category: string;
  inStock: boolean;
}

// Partial<T> - All properties optional
type PartialProduct = Partial<Product>;
// { id?: string; name?: string; price?: number; ... }

// Use case: Update functions
function updateProduct(id: string, updates: Partial<Product>) {
  // Can update any subset of properties
}

updateProduct("1", { price: 899 }); // ✅ OK
updateProduct("1", { price: 899, inStock: true }); // ✅ OK

// Required<T> - All properties required
type RequiredProduct = Required<Product>;
// All properties must be present (opposite of Partial)

// Pick<T, K> - Select specific properties
type ProductSummary = Pick<Product, "id" | "name" | "price">;
// { id: string; name: string; price: number; }

// Use case: API responses with subset of data
function getProductSummaries(): ProductSummary[] {
  // Return only id, name, price
}

// Omit<T, K> - Remove specific properties
type ProductWithoutId = Omit<Product, "id">;
// { name: string; price: number; description: string; ... }

// Use case: Create operations (no id yet)
function createProduct(data: Omit<Product, "id">): Product {
  return {
    id: generateId(),
    ...data
  };
}

// Record<K, T> - Object with specific key and value types
type ProductMap = Record<string, Product>;
// { [key: string]: Product }

const products: ProductMap = {
  "laptop-1": { id: "1", name: "Laptop", /* ... */ },
  "mouse-1": { id: "2", name: "Mouse", /* ... */ }
};

// More specific keys
type PriceByCategory = Record<"electronics" | "clothing" | "books", number>;
const avgPrices: PriceByCategory = {
  electronics: 499,
  clothing: 49,
  books: 15
};

// Readonly<T> - All properties readonly
type ImmutableProduct = Readonly<Product>;

// ReturnType<T> - Extract return type of function
function getProduct(): Product {
  return { id: "1", name: "Laptop", price: 999, /* ... */ };
}

type ProductReturnType = ReturnType<typeof getProduct>; // Product

// Parameters<T> - Extract parameter types
function updatePrice(id: string, price: number): void {}

type UpdatePriceParams = Parameters<typeof updatePrice>; // [string, number]

// Awaited<T> - Unwrap Promise type
type ProductPromise = Promise<Product>;
type UnwrappedProduct = Awaited<ProductPromise>; // Product

async function fetchProduct(): Promise<Product> {
  // ...
}

type FetchedProduct = Awaited<ReturnType<typeof fetchProduct>>; // Product
```

---

### Type Guards and Narrowing

```typescript
// Union type
type PaymentMethod =
  | { type: "credit_card"; cardNumber: string; cvv: string }
  | { type: "paypal"; email: string }
  | { type: "crypto"; walletAddress: string };

// Type guard with 'in' operator
function processPayment(method: PaymentMethod) {
  if ("cardNumber" in method) {
    // TypeScript knows method is credit_card
    console.log(method.cardNumber);
  } else if ("email" in method) {
    // TypeScript knows method is paypal
    console.log(method.email);
  } else {
    // TypeScript knows method is crypto
    console.log(method.walletAddress);
  }
}

// Discriminated unions (recommended approach)
type PaymentMethodDiscriminated =
  | { type: "credit_card"; cardNumber: string; cvv: string }
  | { type: "paypal"; email: string }
  | { type: "crypto"; walletAddress: string };

function processPaymentBetter(method: PaymentMethodDiscriminated) {
  switch (method.type) {
    case "credit_card":
      console.log(method.cardNumber); // Type narrowed
      break;
    case "paypal":
      console.log(method.email); // Type narrowed
      break;
    case "crypto":
      console.log(method.walletAddress); // Type narrowed
      break;
  }
}

// Custom type guards
function isProduct(obj: any): obj is Product {
  return (
    typeof obj === "object" &&
    typeof obj.id === "string" &&
    typeof obj.name === "string" &&
    typeof obj.price === "number"
  );
}

function processData(data: unknown) {
  if (isProduct(data)) {
    // TypeScript knows data is Product
    console.log(data.price);
  }
}

// typeof type guard
function processValue(value: string | number) {
  if (typeof value === "string") {
    console.log(value.toUpperCase()); // Type: string
  } else {
    console.log(value.toFixed(2)); // Type: number
  }
}

// instanceof type guard
class ProductModel {
  constructor(public name: string) {}
}

function process(item: ProductModel | string) {
  if (item instanceof ProductModel) {
    console.log(item.name); // Type: ProductModel
  } else {
    console.log(item.toUpperCase()); // Type: string
  }
}

// Truthiness narrowing
function processOptional(value: string | null | undefined) {
  if (value) {
    console.log(value.toUpperCase()); // Type: string
  }
}
```

---

## React Fundamentals

### Functional Components

```typescript
// Basic component
function Greeting() {
  return <h1>Hello, World!</h1>;
}

// Component with props (TypeScript)
interface GreetingProps {
  name: string;
  age?: number; // Optional
}

function Greeting({ name, age }: GreetingProps) {
  return (
    <div>
      <h1>Hello, {name}!</h1>
      {age && <p>Age: {age}</p>}
    </div>
  );
}

// Alternative: React.FC (FunctionComponent)
const Greeting: React.FC<GreetingProps> = ({ name, age }) => {
  return (
    <div>
      <h1>Hello, {name}!</h1>
      {age && <p>Age: {age}</p>}
    </div>
  );
};

// With children
interface CardProps {
  title: string;
  children: React.ReactNode;
}

function Card({ title, children }: CardProps) {
  return (
    <div className="card">
      <h2>{title}</h2>
      <div>{children}</div>
    </div>
  );
}

// Usage
<Card title="Product">
  <p>Product description</p>
  <button>Buy Now</button>
</Card>
```

---

### Props and State

```typescript
// Props interface
interface ProductCardProps {
  product: Product;
  onAddToCart: (productId: string) => void;
  featured?: boolean;
}

function ProductCard({ product, onAddToCart, featured = false }: ProductCardProps) {
  return (
    <div className={featured ? "featured" : ""}>
      <h3>{product.name}</h3>
      <p>${product.price}</p>
      <button onClick={() => onAddToCart(product.id)}>
        Add to Cart
      </button>
    </div>
  );
}

// Destructuring with defaults
interface ButtonProps {
  label: string;
  variant?: "primary" | "secondary";
  size?: "small" | "medium" | "large";
}

function Button({
  label,
  variant = "primary",
  size = "medium"
}: ButtonProps) {
  return (
    <button className={`btn-${variant} btn-${size}`}>
      {label}
    </button>
  );
}

// Rest props (spreading additional props)
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
}

function Button({ variant = "primary", children, ...rest }: ButtonProps) {
  return (
    <button className={`btn-${variant}`} {...rest}>
      {children}
    </button>
  );
}

// Usage: can pass any button props
<Button variant="primary" onClick={handleClick} disabled>
  Click me
</Button>
```

---

## React Hooks Deep Dive

### useState

```typescript
import { useState } from "react";

// Basic usage
function Counter() {
  const [count, setCount] = useState(0); // Type inferred: number

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
      <button onClick={() => setCount(prev => prev + 1)}>Increment (functional)</button>
    </div>
  );
}

// With explicit type
interface User {
  id: string;
  name: string;
}

function UserProfile() {
  const [user, setUser] = useState<User | null>(null);

  return (
    <div>
      {user ? <p>Hello, {user.name}!</p> : <p>Loading...</p>}
    </div>
  );
}

// Complex state (object)
interface FormData {
  email: string;
  password: string;
}

function LoginForm() {
  const [formData, setFormData] = useState<FormData>({
    email: "",
    password: ""
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  return (
    <form>
      <input
        name="email"
        value={formData.email}
        onChange={handleChange}
      />
      <input
        name="password"
        type="password"
        value={formData.password}
        onChange={handleChange}
      />
    </form>
  );
}

// Lazy initialization (expensive computation)
function ExpensiveComponent() {
  // Function only runs on initial render
  const [data, setData] = useState(() => {
    return computeExpensiveValue();
  });

  return <div>{data}</div>;
}
```

---

### useEffect

```typescript
import { useEffect, useState } from "react";

// Basic usage - runs after every render
function Example() {
  useEffect(() => {
    console.log("Component rendered");
  });

  return <div>Example</div>;
}

// With dependency array - runs on mount and when dependencies change
function ProductDetails({ productId }: { productId: string }) {
  const [product, setProduct] = useState<Product | null>(null);

  useEffect(() => {
    async function fetchProduct() {
      const response = await fetch(`/api/products/${productId}`);
      const data = await response.json();
      setProduct(data);
    }

    fetchProduct();
  }, [productId]); // Re-run when productId changes

  return <div>{product?.name}</div>;
}

// Empty dependency array - runs once on mount
function Analytics() {
  useEffect(() => {
    console.log("Component mounted");

    // Cleanup function - runs on unmount
    return () => {
      console.log("Component unmounted");
    };
  }, []); // Empty array = run once

  return <div>Analytics</div>;
}

// Cleanup example - subscriptions
function RealtimePrice({ productId }: { productId: string }) {
  const [price, setPrice] = useState<number>(0);

  useEffect(() => {
    // Subscribe to price updates
    const unsubscribe = subscribeToPrice(productId, (newPrice) => {
      setPrice(newPrice);
    });

    // Cleanup: unsubscribe when component unmounts or productId changes
    return () => {
      unsubscribe();
    };
  }, [productId]);

  return <div>Current price: ${price}</div>;
}

// Multiple effects - separate concerns
function UserDashboard({ userId }: { userId: string }) {
  const [user, setUser] = useState<User | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);

  // Effect 1: Fetch user
  useEffect(() => {
    fetchUser(userId).then(setUser);
  }, [userId]);

  // Effect 2: Fetch orders
  useEffect(() => {
    fetchOrders(userId).then(setOrders);
  }, [userId]);

  return <div>{/* ... */}</div>;
}

// Common mistake: missing dependencies
function BuggyComponent({ userId }: { userId: string }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    // ❌ Bug: userId is used but not in dependency array
    fetchData(userId).then(setData);
  }, []); // Should be [userId]

  return <div>{/* ... */}</div>;
}

// ESLint plugin: eslint-plugin-react-hooks catches these mistakes
```

---

### useCallback

**Memoizes a function to prevent unnecessary re-creation.**

```typescript
import { useCallback, useState } from "react";

// Without useCallback - function recreated on every render
function ProductList() {
  const [products, setProducts] = useState<Product[]>([]);

  // ❌ New function on every render
  const handleAddToCart = (productId: string) => {
    console.log("Adding to cart:", productId);
  };

  return (
    <div>
      {products.map(product => (
        <ProductCard
          key={product.id}
          product={product}
          onAddToCart={handleAddToCart} // New function = ProductCard re-renders
        />
      ))}
    </div>
  );
}

// With useCallback - function only recreated when dependencies change
function ProductListOptimized() {
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<string[]>([]);

  // ✅ Function memoized, only recreated when setCart changes (never)
  const handleAddToCart = useCallback((productId: string) => {
    setCart(prev => [...prev, productId]);
  }, []); // Empty deps = never recreated

  return (
    <div>
      {products.map(product => (
        <ProductCard
          key={product.id}
          product={product}
          onAddToCart={handleAddToCart} // Same function reference
        />
      ))}
    </div>
  );
}

// With dependencies
function SearchResults() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Filters>({});

  // Function recreated when query or filters change
  const handleSearch = useCallback(() => {
    performSearch(query, filters);
  }, [query, filters]);

  return <SearchBar onSearch={handleSearch} />;
}

// TypeScript typing
interface Callback {
  (id: string): void;
}

const handleClick: Callback = useCallback((id: string) => {
  console.log(id);
}, []);
```

**When to use useCallback?**
- Passing callbacks to optimized child components (wrapped in `React.memo`)
- Dependency of `useEffect` or other hooks
- Expensive function creation

**When NOT to use?**
- Simple inline functions
- Not passed to child components
- Premature optimization

---

### useMemo

**Memoizes a computed value to avoid expensive recalculations.**

```typescript
import { useMemo, useState } from "react";

// Without useMemo - recalculated on every render
function ProductList() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filter, setFilter] = useState("");

  // ❌ Filtered every render, even if products/filter unchanged
  const filteredProducts = products.filter(p =>
    p.name.toLowerCase().includes(filter.toLowerCase())
  );

  return <div>{/* render filteredProducts */}</div>;
}

// With useMemo - only recalculated when dependencies change
function ProductListOptimized() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filter, setFilter] = useState("");

  // ✅ Only recalculated when products or filter change
  const filteredProducts = useMemo(() => {
    console.log("Filtering products...");
    return products.filter(p =>
      p.name.toLowerCase().includes(filter.toLowerCase())
    );
  }, [products, filter]);

  return <div>{/* render filteredProducts */}</div>;
}

// Expensive calculation
function ShoppingCart() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [taxRate, setTaxRate] = useState(0.08);

  // Calculate total (might be expensive with many items)
  const total = useMemo(() => {
    console.log("Calculating total...");
    const subtotal = items.reduce((sum, item) =>
      sum + (item.price * item.quantity), 0
    );
    return subtotal * (1 + taxRate);
  }, [items, taxRate]);

  return (
    <div>
      <p>Total: ${total.toFixed(2)}</p>
    </div>
  );
}

// Memoizing object creation (prevent re-renders)
function UserProfile() {
  const [firstName, setFirstName] = useState("John");
  const [lastName, setLastName] = useState("Doe");

  // ❌ New object every render = child re-renders
  const user = { firstName, lastName };

  // ✅ Same object reference unless firstName/lastName change
  const userMemo = useMemo(() => ({
    firstName,
    lastName
  }), [firstName, lastName]);

  return <UserCard user={userMemo} />;
}

// TypeScript typing
const expensiveValue: number = useMemo(() => {
  return computeExpensiveValue();
}, []);
```

**When to use useMemo?**
- Expensive calculations (filtering large arrays, complex math)
- Creating objects/arrays passed to child components
- Preventing unnecessary re-renders

**When NOT to use?**
- Simple calculations (addition, string concatenation)
- Premature optimization
- Not passed to children

---

### useReducer

**Alternative to useState for complex state logic.**

```typescript
import { useReducer } from "react";

// Define state type
interface CartState {
  items: CartItem[];
  total: number;
}

// Define action types
type CartAction =
  | { type: "ADD_ITEM"; payload: CartItem }
  | { type: "REMOVE_ITEM"; payload: string }
  | { type: "UPDATE_QUANTITY"; payload: { id: string; quantity: number } }
  | { type: "CLEAR_CART" };

// Reducer function
function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "ADD_ITEM":
      const existingItem = state.items.find(item => item.id === action.payload.id);

      if (existingItem) {
        // Update quantity
        return {
          ...state,
          items: state.items.map(item =>
            item.id === action.payload.id
              ? { ...item, quantity: item.quantity + action.payload.quantity }
              : item
          )
        };
      } else {
        // Add new item
        return {
          ...state,
          items: [...state.items, action.payload]
        };
      }

    case "REMOVE_ITEM":
      return {
        ...state,
        items: state.items.filter(item => item.id !== action.payload)
      };

    case "UPDATE_QUANTITY":
      return {
        ...state,
        items: state.items.map(item =>
          item.id === action.payload.id
            ? { ...item, quantity: action.payload.quantity }
            : item
        )
      };

    case "CLEAR_CART":
      return {
        items: [],
        total: 0
      };

    default:
      return state;
  }
}

// Component using useReducer
function ShoppingCart() {
  const [state, dispatch] = useReducer(cartReducer, {
    items: [],
    total: 0
  });

  const addToCart = (item: CartItem) => {
    dispatch({ type: "ADD_ITEM", payload: item });
  };

  const removeFromCart = (id: string) => {
    dispatch({ type: "REMOVE_ITEM", payload: id });
  };

  const updateQuantity = (id: string, quantity: number) => {
    dispatch({ type: "UPDATE_QUANTITY", payload: { id, quantity } });
  };

  const clearCart = () => {
    dispatch({ type: "CLEAR_CART" });
  };

  return (
    <div>
      {state.items.map(item => (
        <CartItem
          key={item.id}
          item={item}
          onRemove={() => removeFromCart(item.id)}
          onUpdateQuantity={(qty) => updateQuantity(item.id, qty)}
        />
      ))}
      <button onClick={clearCart}>Clear Cart</button>
    </div>
  );
}

// useReducer with init function (lazy initialization)
function TodoApp() {
  const init = (initialCount: number) => {
    return { count: initialCount };
  };

  const [state, dispatch] = useReducer(reducer, 0, init);
  // init function runs once with 0 as argument
}
```

**useState vs useReducer?**

Use **useState** when:
- Simple state (boolean, number, string)
- Independent state updates
- Few state transitions

Use **useReducer** when:
- Complex state (objects with multiple fields)
- State transitions depend on previous state
- Multiple related state updates
- Complex update logic

---

### useRef

**Persist values between renders without causing re-renders.**

```typescript
import { useRef, useEffect } from "react";

// Access DOM elements
function FocusInput() {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus();
  }, []);

  return <input ref={inputRef} type="text" />;
}

// Store previous value
function Counter() {
  const [count, setCount] = useState(0);
  const prevCountRef = useRef<number>();

  useEffect(() => {
    prevCountRef.current = count;
  }, [count]);

  return (
    <div>
      <p>Current: {count}</p>
      <p>Previous: {prevCountRef.current}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}

// Store mutable value (doesn't cause re-render)
function Timer() {
  const [seconds, setSeconds] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout>();

  const startTimer = () => {
    intervalRef.current = setInterval(() => {
      setSeconds(s => s + 1);
    }, 1000);
  };

  const stopTimer = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };

  useEffect(() => {
    return () => stopTimer(); // Cleanup
  }, []);

  return (
    <div>
      <p>Seconds: {seconds}</p>
      <button onClick={startTimer}>Start</button>
      <button onClick={stopTimer}>Stop</button>
    </div>
  );
}

// Avoid recreating functions/objects
function ExpensiveComponent() {
  // ❌ New function every render
  const processData = (data: any) => { /* ... */ };

  // ✅ Same function instance
  const processDataRef = useRef((data: any) => { /* ... */ });

  return <div>{/* ... */}</div>;
}
```

**useRef vs useState?**

- **useRef**: Value persists, changing it doesn't cause re-render
- **useState**: Value persists, changing it causes re-render

---

### Custom Hooks

**Extract reusable logic into custom hooks.**

```typescript
// Custom hook for fetching data
function useFetch<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(url);
        const json = await response.json();
        setData(json);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [url]);

  return { data, loading, error };
}

// Usage
function ProductDetails({ id }: { id: string }) {
  const { data, loading, error } = useFetch<Product>(`/api/products/${id}`);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!data) return <div>No product found</div>;

  return <div>{data.name}</div>;
}

// Custom hook for local storage
function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initialValue;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue] as const;
}

// Usage
function ThemeToggle() {
  const [theme, setTheme] = useLocalStorage<"light" | "dark">("theme", "light");

  return (
    <button onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
      Current theme: {theme}
    </button>
  );
}

// Custom hook for debounced value
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Usage
function SearchInput() {
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  useEffect(() => {
    if (debouncedSearchTerm) {
      // API call only happens 500ms after user stops typing
      searchAPI(debouncedSearchTerm);
    }
  }, [debouncedSearchTerm]);

  return (
    <input
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
    />
  );
}
```

---

## React Performance Patterns

### React.memo

**Prevents re-renders when props haven't changed.**

```typescript
import { memo } from "react";

// Without memo - re-renders every time parent renders
function ProductCard({ product }: { product: Product }) {
  console.log("Rendering ProductCard");
  return <div>{product.name}</div>;
}

// With memo - only re-renders when product changes
const ProductCardMemo = memo(function ProductCard({ product }: { product: Product }) {
  console.log("Rendering ProductCard");
  return <div>{product.name}</div>;
});

// Custom comparison function
const ProductCardCustom = memo(
  function ProductCard({ product }: { product: Product }) {
    return <div>{product.name}</div>;
  },
  (prevProps, nextProps) => {
    // Return true if props are equal (don't re-render)
    // Return false if props changed (re-render)
    return prevProps.product.id === nextProps.product.id;
  }
);

// Usage
function ProductList() {
  const [products, setProducts] = useState<Product[]>([]);
  const [count, setCount] = useState(0);

  return (
    <div>
      <button onClick={() => setCount(count + 1)}>Count: {count}</button>
      {products.map(product => (
        // ProductCardMemo won't re-render when count changes
        <ProductCardMemo key={product.id} product={product} />
      ))}
    </div>
  );
}
```

---

### Code Splitting (Lazy Loading)

```typescript
import { lazy, Suspense } from "react";

// Lazy load component
const ProductDetails = lazy(() => import("./ProductDetails"));
const AdminDashboard = lazy(() => import("./AdminDashboard"));

function App() {
  return (
    <div>
      <Suspense fallback={<div>Loading...</div>}>
        <ProductDetails id="123" />
      </Suspense>
    </div>
  );
}

// Route-based code splitting (React Router)
import { Routes, Route } from "react-router-dom";

const Home = lazy(() => import("./pages/Home"));
const Products = lazy(() => import("./pages/Products"));
const Checkout = lazy(() => import("./pages/Checkout"));

function App() {
  return (
    <Suspense fallback={<div>Loading page...</div>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/products" element={<Products />} />
        <Route path="/checkout" element={<Checkout />} />
      </Routes>
    </Suspense>
  );
}
```

---

### Error Boundaries

```typescript
import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Error caught by boundary:", error, errorInfo);
    // Log to error tracking service (Sentry, etc.)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div>
          <h2>Something went wrong</h2>
          <details>
            <summary>Error details</summary>
            <pre>{this.state.error?.message}</pre>
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}

// Usage
function App() {
  return (
    <ErrorBoundary fallback={<div>Error loading products</div>}>
      <ProductList />
    </ErrorBoundary>
  );
}
```

**Note**: Error boundaries only catch errors in:
- Rendering
- Lifecycle methods
- Constructors

They DON'T catch errors in:
- Event handlers (use try/catch)
- Async code
- Server-side rendering
- Errors in the error boundary itself

---

## Quick Reference

### Hook Rules

1. **Only call hooks at the top level** (not in loops, conditions, nested functions)
2. **Only call hooks from React functions** (components or custom hooks)

```typescript
// ❌ Bad
function Component() {
  if (condition) {
    const [state, setState] = useState(0); // Don't conditionally call hooks
  }

  for (let i = 0; i < 10; i++) {
    useEffect(() => {}); // Don't call in loops
  }
}

// ✅ Good
function Component() {
  const [state, setState] = useState(0);

  useEffect(() => {
    if (condition) {
      // Condition inside hook is fine
    }
  });
}
```

---

### Common Patterns

#### Conditional Rendering

```typescript
// Ternary
{isLoggedIn ? <UserMenu /> : <LoginButton />}

// Logical AND
{products.length > 0 && <ProductList products={products} />}

// Nullish coalescing
{user?.name ?? "Guest"}

// Early return
function ProductDetails({ product }: { product: Product | null }) {
  if (!product) return <div>No product found</div>;

  return <div>{product.name}</div>;
}
```

#### Lists and Keys

```typescript
// Always provide unique key
{products.map(product => (
  <ProductCard key={product.id} product={product} />
))}

// ❌ Don't use index as key (unless list never changes)
{products.map((product, index) => (
  <ProductCard key={index} product={product} />
))}
```

#### Forms

```typescript
function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login(email, password);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button type="submit">Login</button>
    </form>
  );
}
```

---

### TypeScript + React Cheat Sheet

```typescript
// Component props
interface Props {
  title: string;
  count?: number;
  onClick: () => void;
  children: React.ReactNode;
}

// Event handlers
const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {};
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {};
const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {};

// Ref types
const inputRef = useRef<HTMLInputElement>(null);
const divRef = useRef<HTMLDivElement>(null);
const buttonRef = useRef<HTMLButtonElement>(null);

// useState with type
const [user, setUser] = useState<User | null>(null);
const [items, setItems] = useState<Item[]>([]);

// Custom hook return type
function useCustomHook(): [string, (value: string) => void] {
  // ...
  return [value, setValue];
}

// Or use 'as const' for tuple
function useCustomHook() {
  // ...
  return [value, setValue] as const;
}
```

---

## Practice Exercises

1. **Create a Product type** with id, name, price, optional reviews
2. **Write a ProductCard component** that accepts a Product and onAddToCart callback
3. **Implement a search filter** using useState and useMemo
4. **Create a custom hook** `useProducts()` that fetches and returns products
5. **Build a shopping cart** using useReducer
