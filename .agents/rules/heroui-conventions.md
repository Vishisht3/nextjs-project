# HeroUI v3 & Tailwind CSS v4 Conventions

This rule provides migration conventions, component mappings, and best practices for `@heroui/react` (v3) in this workspace.

---

## 1. Package & Import Guidelines

* **Package**: Always import from `@heroui/react`. **Never** use `@nextui-org/react`.
* **Animations**: HeroUI v3 is built on React Aria and Tailwind CSS v4 transitions; `framer-motion` is **not** required. If custom animations are needed, use `motion` (`import { motion } from "motion/react"`).
* **Styles**: Ensure `globals.css` imports `@import "tailwindcss";` and `@import "@heroui/styles";`.

---

## 2. Component API Cheatsheet

### Card
* **Old (NextUI v2)**: `<Card shadow="sm"><CardBody>...</CardBody></Card>`
* **HeroUI v3**:
  ```tsx
  import { Card } from "@heroui/react";

  <Card className="bg-content1 shadow-sm">
    <Card.Header>
      <Card.Title>Title</Card.Title>
      <Card.Description>Description</Card.Description>
    </Card.Header>
    <Card.Content>
      {/* Content goes here */}
    </Card.Content>
    <Card.Footer>Footer</Card.Footer>
  </Card>
  ```
* **Notice**: No `shadow="..."` prop; use Tailwind classes like `shadow-sm` directly on `className`.

---

### Button
* **Old (NextUI v2)**: `<Button color="primary" isLoading={loading}>`
* **HeroUI v3**:
  ```tsx
  import { Button, Spinner } from "@heroui/react";

  <Button
    variant="primary"
    isDisabled={isLoading}
    onClick={handleClick}
  >
    {isLoading ? <Spinner size="sm" color="current" /> : "Submit"}
  </Button>
  ```
* **Variants**: `"primary" | "secondary" | "tertiary" | "outline" | "ghost" | "danger" | "danger-soft"`
* **Notice**: Use `variant="..."` instead of `color="..."`. Use `isDisabled={isLoading}` instead of `isLoading`.

---

### TextArea & Input
* **Old (NextUI v2)**: `<Textarea minRows={1} maxRows={4} />`
* **HeroUI v3**:
  ```tsx
  import { TextArea } from "@heroui/react";

  <TextArea
    rows={2}
    placeholder="Type message..."
    value={value}
    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setValue(e.target.value)}
    onKeyDown={handleKeyDown}
    className="w-full"
  />
  ```
* **Notice**:
  * Capitalized as `TextArea` (not `Textarea`).
  * Explicitly type change events with `React.ChangeEvent<HTMLTextAreaElement>`.
  * Use standard HTML attributes like `rows={2}` instead of `minRows`/`maxRows`.

---

### Accordion
* **Old (NextUI v2)**: `<Accordion><AccordionItem title="...">Content</AccordionItem></Accordion>`
* **HeroUI v3** (Compound component pattern):
  ```tsx
  import { Accordion } from "@heroui/react";

  <Accordion className="px-0">
    <Accordion.Item id="item-1">
      <Accordion.Heading>
        <Accordion.Trigger className="flex items-center justify-between w-full py-2">
          <span>Accordion Title</span>
          <Accordion.Indicator />
        </Accordion.Trigger>
      </Accordion.Heading>
      <Accordion.Panel>
        <Accordion.Body className="py-2">
          Accordion Content
        </Accordion.Body>
      </Accordion.Panel>
    </Accordion.Item>
  </Accordion>
  ```

---

### Chip
* **Old (NextUI v2)**: `<Chip color="secondary" variant="flat">`
* **HeroUI v3**:
  ```tsx
  import { Chip } from "@heroui/react";

  <Chip size="sm" variant="soft" color="accent">
    Tag
  </Chip>
  ```
* **Color options**: `"accent" | "danger" | "default" | "success" | "warning"`
* **Variant options**: `"primary" | "secondary" | "soft" | "tertiary"`

---

### Spinner
* **HeroUI v3**:
  ```tsx
  import { Spinner } from "@heroui/react";

  <Spinner size="sm" color="current" />
  ```
* **Color options**: `"accent" | "current" | "danger" | "success" | "warning"`
* **Size options**: `"sm" | "md" | "lg" | "xl"`

---

### Avatar
* **HeroUI v3**:
  ```tsx
  import { Avatar } from "@heroui/react";

  <Avatar className="ring-2 ring-primary">
    <Avatar.Fallback>AI</Avatar.Fallback>
  </Avatar>
  ```
